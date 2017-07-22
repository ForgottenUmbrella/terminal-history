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
        self.current_line = None
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
            prev_line_ended = (
                self.current_line is None or self.current_line[-1] == "\n"
                )
            if prev_line_ended:
                self._reset_line(line)
            else:
                self.current_line += line
        logging.debug(f"self.current_line = {repr(self.current_line)}")
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
        # Make a copy so the original doesn't get modified.
        line = self.current_line
        logging.info(f"line = {repr(line)}")
        # Remove zero-space characters (\a).
        line = line.replace("\a", "")
        logging.debug(f"(a) line = {repr(line)}")
        # Consider final output after carriage returns.
        line = line.split("\r")[-1]
        logging.debug(f"(r) line = {repr(line)}")
        # Consider final output after characters that shouldn't be used.
        line = expand_obscure_chars(line).split("\n")[-1]
        logging.debug(f"(vt,ff) line = {repr(line)}")
        # Represent non-monospace tabs as multiple spaces.
        line = line.expandtabs()
        logging.debug(f"(t) line = {repr(line)}")
        # Backspaces should be negative length, so just get rid of them.
        line = apply_bs(line)
        logging.debug(f"(b) line = {repr(line)}")
        # Handle long lines.
        line = terminal_wrap(line)[-1]
        logging.debug(f"(%) line = {repr(line)}")

        # XXX
        # terminal_width = shutil.get_terminal_size().columns
        # logging.debug(f"terminal_width = {terminal_width}")
        line_length = len(line)
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
        # # Powershell due to it handling backspaces weirdly. Consider
        # # using a better OS.
        # line_length %= terminal_width
        # logging.info(f"(%) line_length = {line_length}")

        self.builtin_print(
            f"\x1b[{line_length}C\x1b[1A", end="", flush=True
            )

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
        logging.debug(f"line = {repr(text)}")
        return

    def _reset_line(self, text):
        """Append to `self.lines` instead."""
        self.lines.append(text)


def expand_obscure_chars(text):
    """Return expansion of formfeeds and vertical tabs."""
    # Make handling splitting easier.
    text = text.replace("\f", "\v")
    parts = text.split("\v")
    rep = parts[0]
    for i, part in enumerate(parts[1:]):
        so_far = "".join(parts[:i])
        rep += "\n" + " " * len(so_far) + part
    return rep


def terminal_wrap(text):
    """Return a list of lines, wrapped weirdly."""
    terminal_width = shutil.get_terminal_size().columns
    # XXX
    # lines = textwrap.wrap(
    #     text, width=terminal_width, expand_tabs=False,
    #     replace_whitespace=False, drop_whitespace=False,
    #     break_long_words=True, break_on_hyphens=True
    #     )
    # segment_before = text[:terminal_width]
    # logging.info(f"segment_before = {repr(segment_before)}")
    # segment_after = text[terminal_width + len(prev_segment):]
    # logging.info(f"segment_after = {repr(segment_after)}")
    # text = segment_before + segment_after
    # logging.info(f"text = {repr(text)}")
    lines = []
    for i in range(0, len(text), terminal_width):
        chunk = text[i:terminal_width]
        if chunk:
            lines.append(chunk)
    logging.info(f"lines = {lines}")
    return lines


def apply_bs(text):
    """Return text with backspaces replaced with nothing."""
    original = text
    regex = re.compile(".\b")
    logging.debug(f"(bs) match = {regex.search(text)}")
    while regex.search(text):
        # Ensure "\b\b" doesn't backspace itself.
        text = re.sub(regex, "", text, count=1)
    # NOTE: Incompatible with PowerShell.
    text = text.lstrip("\b")
    if text != original:
        logging.debug(f"(bs) before, text ={repr(original)}")
        logging.debug(f"(bs) after, text ={repr(text)}")
    return text


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

    # hello = "Hello, "
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
