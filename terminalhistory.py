#!/usr/bin/env python3
# encoding=utf-8
"""Provide classes for storing lines from the terminal."""
import sys
import os
import platform
import shutil
import re
import logging

logging.basicConfig(level=logging.INFO, filename="log.log", filemode="w")

if platform.system() == "Windows":
    try:
        # Enable ANSI support (for Windows 10 >= v1511).
        import colorama
    except ImportError:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    else:
        colorama.init()
else:
    import readline  # pylint: disable=unused-import


class TempHistory:
    """Record the current printing line from the terminal.

    Note: I use the term "echo" to refer to when text is
    shown on the terminal but might not be written to `sys.stdout`.
    """

    def __init__(self):
        """Initialise variables and save overwritten built-ins."""
        self.current_line = ""
        # Used to handle long lines.
        self._prev_segment = ""
        self.builtin_print = print
        self.builtin_input = input

    def _reset_line(self, text):
        """Assign `text` to `self.current_line` once it has terminated.

        To be overridden by child classes.
        """
        self.current_line = text


    def _record(self, text):
        """Change `self.current_line` to reflect the current line.

        `text` may be empty, for flexibility, in which case nothing
        happens.
        """
        # Allow flexibility in calling the method.
        if text == "":
            logging.debug("Premature return from _record.")
            return

        lines = text.splitlines(True)
        # Ensure the last line in `lines` is the current available line.
        if lines[-1][-1] == "\n":
            lines.append("")

        for line in lines:
            prev_line_ended = (self.current_line[-1] == "\n")
            if prev_line_ended:
                self._prev_segment = ""
                self._reset_line(line)
            else:
                self._prev_segment = self.current_line
                self.current_line += line

        # XXX
        # if prev_line_ended:
        #     # Account for `handle_bs` being unable to remove backspaces
        #     # at the start of lines due to having no context.
        #     # `.lstrip` can't be called in `handle_bs` because
        #     # backspaces at the start could be valid when text comes
        #     # after a line without a newline.
        #     # NOTE: This is incompatible with Windows Powershell.
        #     self.current_line = last_line.lstrip("\b")
        # else:
        #     self._prev_segment = self.current_line
        #     self.current_line += lines[-1]
        #     # Account for potential backspace in beginning of the last
        #     # line combining with `self.current_line` to form regex match which
        #     # should be removed.
        #     self.current_line = handle_bs(self.current_line)
        logging.info(f"self.current_line = {repr(self.current_line)}")
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
        line = self.current_line.expandtabs()
        # terminal_width = shutil.get_terminal_size().columns
        # logging.info(f"terminal_width = {terminal_width}")
        line_length = len(self.current_line)
        # logging.info(f"self.current_line = {repr(self.current_line)}")
        # logging.info(f"(original) line_length = {line_length}")
        # if line_length > terminal_width:
        #     # Modulo the previous segment to handle wrapping if it was
        #     # really long.
        #     prev_length = len(self._prev_segment) % terminal_width
        #     logging.info(f"self._prev_segment = {repr(self._prev_segment)}")
        #     logging.info(f"(%) prev_length = {prev_length}")
        #     line_length -= prev_length
        #     logging.info(f"(-) line_length = {line_length}")
        # # Modulo the width to handle the long current line wrapping.
        # # NOTE: Modulo operations are incompatible with Windows
        # Powershell due to it handling backspaces weirdly. Consider
        # using a better OS.
        # line_length %= terminal_width
        # logging.info(f"(%) line_length = {line_length}")
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
    """Record all lines from the terminal."""

    def __init__(self):
        """Initialise the list of terminal lines."""
        # Needs to be defined before super because of `line` property.
        # self.lines = [None]
        self.lines = []
        super().__init__()

    @property
    def current_line(self):
        """Return the current line."""
        # If `self.lines` hasn't been initialised yet, it'll fail.
        try:
            return self.lines[-1]
        except IndexError:
            logging.debug("line referenced but not yet initialised.")
            return None

    @current_line.setter
    def current_line(self, text):
        """Set the current line."""
        try:
            self.lines[-1] = text
        except IndexError:
            logging.debug("Attempted to assign to line, not yet initialised.")
            return
        logging.info(f"line = {repr(text)}")
        return

    def _reset_line(self, text):
        """Append to `self.lines` instead."""
        self.lines.append(text)


    # def _record(self, text):
    #     """Append `text` to current `line` or list of `lines`.

    #     Overrides parent  `_record' method, preventing overwriting when
    #     the line is finished and instead simply creating another line.
    #     """
    #     # TODO: expandtabs for everything
    #     if text == "":
    #         logging.debug("Premature return from _record.")
    #         return
    #     lines = handle_nl(text)
    #     prev_line_ended = (self.current_line[-1] == "\n")

    #     for line in lines:
    #         if prev_line_ended:
    #             self.lines.append(line.lstrip("\b"))
    #         else:
    #             self._prev_segment = self.current_line
    #             # self.current_line = (self.current_line + line).expandtabs()
    #             self.current_line += line
    #             self.current_line = handle_bs(self.current_line)


def handle_bs(text):
    """Return text with backspaces replaced with nothing."""
    original = text
    regex = re.compile(".\b")
    logging.debug(f"(bs) match = {regex.search(text)}")
    text = re.sub(regex, "", text)
    if text != original:
        logging.debug(f"(bs) before, text ={repr(original)}")
        logging.debug(f"(bs) after, text ={repr(text)}")
    return text


def handle_cr(text):
    """Return final text from carriage return abuse."""
    text_versions = text.split("\r")
    real_text = text_versions[-1]
    if real_text != text:
        logging.debug(f"(cr) before, text ={repr(text)}")
        logging.debug(f"(cr) after, text={repr(real_text)}")
    return real_text


def _enable_print_after_input(record_all=False):
    """Conveniently shadow built-in functions.

    Use either `TempHistory` or `TerminalHistory` (which consumes more
    memory), for testing purposes.
    """
    global print  # pylint: disable=global-variable-undefined
    global input  # pylint: disable=global-variable-undefined
    if record_all:
        record = TerminalHistory()
    else:
        record = TempHistory()
    print = record.print  # pylint: disable=redefined-builtin
    input = record.input  # pylint: disable=redefined-builtin


def enable_print_after_input():
    """Conveniently shadow built-in `print` and `input` functions."""
    _enable_print_after_input(record_all=False)


if __name__ == "__main__":
    enable_print_after_input()
    # _enable_print_after_input(record_all=True)

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
