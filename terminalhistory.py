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
        self.TERMINATOR = "\n"
        self.line = self.TERMINATOR
        self.builtin_print = print
        self.builtin_input = input

    def _handle_bs(self, text):
        """Expand backspaces."""
        logging.info(f"(_bs) before, text =\n{repr(text)}")
        regex = re.compile(".\b")
        while regex.match(text):
            logging.info(f"match = {regex.match(text)}")
            text = re.sub(regex, "", text)
            logging.info(f"(_bs) after, text =\n{repr(text)}")
        return text

    def _record(self, text):
        """Append `text` to `line` or overwrite it if it has ended.

        `text` may be empty, for flexibility, in which case nothing
        happens.

        """
        text = self._handle_bs(text)
        if text == "":
            # Allow flexibility in calling the method.
            logging.debug("Premature return from _record.")
            return
        lines = text.split(self.TERMINATOR)
        # If `text` has terminated, then `lines` will not have the
        # termination stored, since it was formed by using the
        # terminator as a delimiter. Take this into account by reading
        # the "second last" line instead, with the terminator affixed.
        if text[-1] == self.TERMINATOR:
            last_line = lines[-2] + self.TERMINATOR
        else:
            last_line = lines[-1]
        # Take into account carriage return abuse.
        last_line = last_line.split("\r")[-1]
        line_has_ended = (self.line[-1] == self.TERMINATOR)
        if line_has_ended:
            self.line = last_line
        else:
            self.line += last_line
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
        # line_length = len(self.line.lstrip("\b"))
        line_length = len(self.line)
        self.builtin_print(
            f"\x1b[{line_length}C\x1b[1A", end="", flush=True
            )
        logging.debug(f"line_length = {line_length}")

    def print(
            self, *values, sep=" ", end="\n", file=sys.stdout, flush=False):
        """Print to `file` and record the printed text.

        Other than recording the printed text, it behaves exactly like
        the built-in `print` function.

        """
        self.builtin_print(*values, sep=sep, end=end, file=file, flush=flush)
        logging.debug(f"file = {file}")
        if file == sys.stdout:
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
        self.line = ""

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
        """Append `text` to `line` or `lines`.

        Overrides TempHistory's `_record' method, preventing overwriting
        when the line is finished and instead simply creating another
        line.

        """
        text = self._handle_bs(text)
        # TODO: expandtabs for everything
        if text == "":
            return
        lines = [
            line.split("\r")[-1] + self.TERMINATOR
            for line in text.split(self.TERMINATOR) if line
            ]
        if text[-1] != self.TERMINATOR:
            lines[-1] = lines[-1][:-1]
        for line in lines:
            if self.line == "":
                self.line = line
            elif self.line[-1] == self.TERMINATOR:
                self.lines.append(line)
            else:
                # self.line = (self.line + line).expandtabs()
                self.line = self.line + line
        return


def enable_print_after_input():
    """Overshadow the built-in `print` and `input` functions."""
    global print
    global input
    record = TerminalHistory()
    print = record.print
    input = record.input


if __name__ == "__main__":
    enable_print_after_input()

    print("\b\bHello, ", end="", flush=True)
    name = input(newline=False)
    print(", how do you do?")
    print("next line")
