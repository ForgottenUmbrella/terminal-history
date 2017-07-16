#!/usr/bin/env python3
# encoding=utf-8
"""Provide classes for storing lines from the terminal."""
import sys
import os
import platform
import re
import logging

logging.basicConfig(level=logging.INFO, filename="log.log", filemode="w")

if platform.system() == "Windows":
    try:
        # Enable ANSI support (for Windows 10 >= v1511).
        import colorama
    except ImportError:
        import ctypes
        KERNEL32 = ctypes.windll.kernel32
        KERNEL32.SetConsoleMode(KERNEL32.GetStdHandle(-11), 7)
    else:
        colorama.init()
else:
    import readline


class TempHistory:
    """Record one line from the terminal.

    Note: I use the term "echo" to refer to when text is
    shown on the terminal but might not be written to `sys.stdout`.

    """

    def __init__(self):
        """Initialise `line` and save the `print` and `input` functions.

        `line` is initially set to "\n" so that the `_record` method
        doesn't raise an error about the string index being out of
        range.
        """
        self.END = "\n"
        self.line = self.END
        self.builtin_print = print
        self.builtin_input = input

    def _record(self, text):
        """Append `text` to `line` or overwrite it if it has ended.

        `text` may be empty, for flexibility, in which case nothing
        happens.

        """
        if text == "":
            # Allow flexibility in calling the method.
            logging.debug("Premature return from _record.")
            return
        lines = handle_nl(text)
        prev_line_ended = (self.line[-1] == self.END)

        if prev_line_ended:
            # Account for `handle_bs` being unable to remove backspaces
            # at the start of lines due to having no context.
            # `.lstrip` can't be called in `handle_bs` because
            # backspaces at the start could be valid when text comes
            # after a line without a newline.
            # NOTE: This is potentially incompatible with Windows'
            # conhost.exe.
            self.line = lines[-1].lstrip("\b")
        else:
            self.line += lines[-1]
            # Account for potential backspace in beginning of the last
            # line combining with `self.line` to form regex match which
            # should be removed.
            self.line = handle_bs(self.line)
        logging.info(f"self.line = {repr(self.line)}")
        return

    def _undo_newline(self):
        """Move text cursor back to its position before echoing newline.

        ANSI escape sequence: "\x1b[{count}{command}"
        "\x1b" is the escape code, and commands "A", "B", "C" and "D"
        are for moving the text cursor up, down, forward and backward
        {count} times respectively.

        Thus, after having echoed a newline, the final statement tells
        the terminal to move the text cursor forward to be in-line with
        the end of the previous line, and then move up into said line
        (making it the current line again).

        """
        line_length = len(self.line)
        self.builtin_print(
            f"\x1b[{line_length}C\x1b[1A", end="", flush=True
            )
        logging.debug(f"line_length = {line_length}")

    def print(
            self, *values, sep=" ", end="\n", file=sys.stdout, flush=False,
            record=True):
        """Print to `file` and record the printed text.

        Other than recording the printed text by default, it behaves
        exactly like the built-in `print` function.

        """
        self.builtin_print(*values, sep=sep, end=end, file=file, flush=flush)
        logging.debug(f"file = {file}")
        if record and file in (sys.stdout, None):
            text = sep.join([str(value) for value in values]) + end
            self._record(text)

    def input(self, prompt="", newline=True):
        """Return one line of user input and record the echoed text.

        Other than storing the echoed text and optionally stripping the
        echoed newline, it behaves exactly like the built-in `input`
        function.

        """
        response = self.builtin_input(prompt)
        using_stdin = (os.fstat(0) == os.fstat(1))
        logging.debug(f"using stdin? {using_stdin}")
        if using_stdin:
            self._record(prompt)
            self._record(response)
        if not newline:
            self._undo_newline()
        return response


class TerminalHistory(TempHistory):
    """Record ALL lines from the terminal (from instantiation onwards)."""

    def __init__(self):
        """Initialise the list of terminal lines."""
        # Needs to be defined before super because of line property.
        self.lines = [""]
        super().__init__()
        self.line = None

    @property
    def line(self):
        """Return the last line."""
        return self.lines[-1]

    @line.setter
    def line(self, text):
        """Set the last line."""
        self.lines[-1] = text
        logging.info(f"line = {repr(text)}")

    def _record(self, text):
        """Append `text` to current `line` or list of `lines`.

        Overrides TempHistory's `_record' method, preventing overwriting
        when the line is finished and instead simply creating another
        line.

        """
        # TODO: expandtabs for everything
        if text == "":
            logging.debug("Premature return from _record.")
            return
        lines = handle_nl(text)
        prev_line_ended = (self.line[-1] == self.END)

        # Handle first assignment's dummy value.
        if self.line is None:
            self.line = lines.pop(0).lstrip("\b")

        for line in lines:
            if prev_line_ended:
                self.lines.append(line.lstrip("\b"))
            else:
                # XXX: self.line = (self.line + line).expandtabs()
                self.line += line
                self.line = handle_bs(self.line)
        return


def handle_bs(text):
    """Return text with backspaces replaced with nothing."""
    original = text
    regex = re.compile(".\b")
    # Do not use the `.match` method. It only works at the beginning of
    # strings.
    while regex.search(text):
        logging.info(f"match = {regex.search(text)}")
        text = re.sub(regex, "", text)
    if text != original:
        logging.info(f"(bs) before, text ={repr(original)}")
        logging.info(f"(bs) after, text ={repr(text)}")
    return text


def handle_cr(text):
    """Return final text from carriage return abuse."""
    text_versions = text.split("\r")
    real_text = text_versions[-1]
    if real_text != text:
        logging.info(f"(cr) before, text ={repr(text)}")
        logging.info(f"(cr) after, text={repr(real_text)}")
    return real_text


def handle_nl(text):
    """Return a list of lines with their terminators attached."""
    END = "\n"
    lines = []
    for line in text.split(END):
        real_line = handle_bs(handle_cr(line))
        # `END` was stripped, so it needs to be appended again.
        real_line += END
        lines.append(real_line)
    text_ended = (text[-1] == END)
    if text_ended:
        # When splitting all terminated lines, the last element of the
        # list was an empty string. One would consider `lines[-2]` to be
        # the true last line, so get rid of the fake.
        lines.pop()
    else:
        # `END` was appended in the loop to all lines, including
        # the last. The last line might not have had an `END`, so
        # it'll need to be stripped again.
        lines[-1] = lines[-1].rstrip(END)
    return lines


def enable_print_after_input(temp=False):
    """Overshadow the built-in `print` and `input` functions."""
    global print
    global input
    record = TerminalHistory()
    # TODO: remove debug
    if temp:
        record = TempHistory()
    print = record.print
    input = record.input


if __name__ == "__main__":
    enable_print_after_input()
    # enable_print_after_input(True)

    # hello = "\b\bHello, "
    # hello = "\bHe\rHello, "
    # hello = "\bHello, "
    # hello = "He\r\b\bHello, "
    # hello = "\r\b\bHello, "
    # hello = "He\r\bHello, "
    hello = "\bHe\b\r\bHell\blo, \b "

    print(hello, end="")
    name = input(newline=False)
    print(" ", end="")
    print("\b, how do you do? ", end="")
    input(newline=False)
    print(". Is this unaligned?")
    # with open("log.log") as log:
    #     for line in log:
    #         sys.stdout.write(line)
