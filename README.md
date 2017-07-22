# Terminal History
[A somewhat cleaner solution](http://stackoverflow.com/a/41436173/6379747) to
the problem of printing on the same line as input. This solution works by
moving the cursor after the terminal echoes the newline, but to do so it needs
to know the length of the terminal's last line, which is why it needs to record
every line written.

## Public Interface
### Classes
* `TempHistory` - class for recording the latest line from the terminal (if you
  use its methods)
* `TerminalHistory` - subclass of TempHistory for recording **all** lines from
  the terminal

### Methods
* `print(*values, sep=" ", end="\n", file=sys.stdout, flush=False, record=True`
- behaves the same as the built-in `print` function, except it also records
  what's printed if `record` is True
* `input(prompt="", record=True, newline=True)` - behaves the same as the
  built-in `input` function, except it also records the prompt and input, as
  well as stripping the newline if `newline` is False

### Attributes
* For TempHistory, `line` - the current available line for echoing
* For TerminalHistory, `lines` - a list of all lines echoed to the terminal via
the `print` and `input` methods

## Functions
* `enable_print_after_input` - convenience function to override the built-in
`print` and `input` functions with ones that record output, enabling printing
after getting input (as the name suggests)

## Example Usage
    import terminalhistory  # What's the convention for naming these anyway?

    enable_print_after_input()

    print("Line one. ", end="")
    input("Also on line one, right? ", newline=False)
    print(". This is also on line one.")

Output (with "yeah" as input):

    Line one. Also on line one, right? yeah. Also on line one.

## To do
* Implement `write` method that replaces `sys.stdout.write` and
  `sys.stderr.write`, behaving almost the same except with the additional
  recording functionality
* Implement `read`, `readline` and `readlines` methods that replace
  `sys.stdin.read`, `sys.stdin.readline` and `sys.stdin.readlines`
  respectively, with recording functionality as well
* Handle long strings when the prompt has escape sequences (due to the built-in
  `input` method, weird wrapping issues occur if you use escape sequences in
  the prompt or `print(prompt, end="")`)
