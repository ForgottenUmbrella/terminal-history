# Terminal History
[A cleaner solution](http://stackoverflow.com/a/41436173/6379747) to the problem of printing on the same line as input. This
solution works by moving the cursor after the newline has been echoed, but in
order to do so effectively it needs to know the length of the terminal's last
line, and therefore needs to record every line written.

## Public Interface
### Classes
* `TempHistory` - class for recording the latest line from the terminal
* `TerminalHistory` - subclass of TempHistory for recording **all** lines from
  the terminal (but only if its methods are used)

### Methods
* `print(*values, sep=' ', end='\n', file=sys.stdout, flush=False, record=True` - behaves the same as the built-in `print` function, except it also
  records what's being printed if `record` is True
* `input(prompt='', record=True, newline=True)` - behaves the same as the built-in `input` function, except it also
  records what's being prompted and typed, as well as stripping the newline if
  `newline` is False

### Attributes
* For TempHistory, `line` - the latest line echoed to the terminal
* For TerminalHistory, `lines` - a list of all lines echoed to the terminal via
  the `print` and `input` methods

## Example Usage
    import terminalhistory  # What's the convention for naming these anyway?

    record = terminalhistory.TempHistory()
    print = record.print  # For convenience
    input = record.input

    # flush=True because otherwise it waits for the line to terminate, which
    # won't happen until the user inputs stuff
    print('line one', end='', flush=True)
    input('unsurprisingly also on line one, right? ', newline=False)
    print('interestingly, also on line one??')

Output:

    line oneunsurprisingly also on line one, right? yeahinterestingly, also on
    line one??

## To do
* Implement `write` method that replaces `sys.stdout.write` and `sys.stderr.write`,
  behaving almost the same except with the additional recording functionality
* Implement `read`, `readline` and `readlines` methods that replace
  `sys.stdin.read`, `sys.stdin.readline` and `sys.stdin.readlines` respectively,
  except with the additional recording functionality as well
