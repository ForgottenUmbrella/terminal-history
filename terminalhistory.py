#!/usr/bin/env python3
# encoding=utf-8
"""Provide classes for storing lines from the terminal."""
import sys
import platform

if platform.system() == "Windows":
    try:
        # Enable ANSI support (for Windows 10 >= v1511)
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
        self.line = "\n"
        self.builtin_print = print
        self.builtin_input = input

    def _record(self, text):
        """Append `text` to `line` or overwrite it if it has ended.

        `text` may be empty, for flexibility, in which case nothing
        happens.

        """
        if text == "":
            # Allow flexibility in calling the method.
            return
        lines = text.split("\n")
        # If `text` has terminated, then `lines` will not have the
        # termination stored, since it was formed by using the
        # terminator as a delimiter. Take this into account by reading
        # the "second last" line instead, with the terminator affixed.
        if text[-1] == "\n":
            last_line = lines[-2] + "\n"
        else:
            last_line = lines[-1]
        # Take into account carriage return abuse.
        last_line = last_line.split("\r")[-1]
        line_has_ended = self.line[-1] == "\n"
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
        line_length = len(self.line)
        # Take into account backspaces.
        for i, char in enumerate(self.line[1:]):
            prev_char = self.line[i-1]
            # HACK: Why must `prev_char` not be a backspace?
            if char == "\b" and prev_char != "\b":
                line_length -= 2
        self.print(f"\x1b[{line_length}C\x1b[1A", end="", flush=True,
                   record=False)

    def print(self, *values, sep=" ", end="\n", file=sys.stdout, flush=False,
              record=True):
        """Print to `file` and record the printed text.

        Other than recording the printed text, it behaves exactly like
        the built-in `print` function.

        """
        self.builtin_print(*values, sep=sep, end=end, file=file, flush=flush)
        if record:
            text = sep.join([str(value) for value in values]) + end
            self._record(text)

    def input(self, prompt="", newline=True, record=True):
        """Return one line of user input and record the echoed text.

        Other than storing the echoed text and optionally stripping the
        echoed newline, it behaves exactly like the built-in `input`
        function.

        """
        if prompt == "":
            # Clear any ghosted output.
            prompt = " \b"
        response = self.builtin_input(prompt)
        if record:
            self._record(prompt)
            self._record(response)
        if not newline:
            self._undo_newline()
        return response


class TerminalHistory(TempHistory):
    """Record ALL lines from the terminal (from instantiation onwards)."""

    def __init__(self):
        """Initialise the list of terminal lines."""
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

    def _record(self, text):
        """Append `text` to `line` or `lines`.

        Overrides TempHistory's `_record' method, preventing overwriting
        when the line is finished and instead simply creating another
        line.

        """
        if text == "" or text == " \b":
            return
        lines = [line.split("\r")[-1] + "\n" for line in text.split("\n") if line]
        if text[-1] != "\n":
            lines[-1] = lines[-1][:-1]
        for line in lines:
            if self.line == "":
                self.line = line
            elif self.line[-1] == "\n":
                self.lines.append(line)
            else:
                self.line += line
        return

if __name__ == "__main__":
    record = TerminalHistory()
    print = record.print
    input = record.input

    print("\b\bHello, ", end="", flush=True)
    name = input(newline=False)
    print(", how do you do?")
    print("next line")
