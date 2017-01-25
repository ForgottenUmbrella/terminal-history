# Terminal History
[Another solution](http://stackoverflow.com/a/41436173/6379747) to the problem of printing on the same line as input. This
solution works by moving the cursor after the newline has been echoed, but in
order to do so effectively it needs to know the length of the terminal's last
line, and therefore needs to record every line written.

This is a much cleaner solution that doesn't reimplement the entire built-in
function, leaving all the nasty logic-handling to it. As a bonus, you can go
look at every single line printed or typed to the terminal (provided you use
its methods) for whatever purpose you might have.

## Usage
    import terminalhistory  # What's the convention for naming these anyway?

    terminal = terminalhistory.TerminalHistory()
    print = terminal.print  # For convenience
    input = terminal.input

    # Notice how it implements the built-in `print` function's arguments
    # flush=True because otherwise it waits for the line to terminate, which
    # won't happen until the user inputs stuff
    print('line one', end='', flush=True)
    # Given that this method shadows the real `input` function, it should
    # behave similarly - it requires an explicit `newline=False` argument
    # to undo the echoed newline
    input('unsurprisingly also on line one, right? ', newline=False)
    print('interestingly, also on line one??')

Output:

    line oneunsurprisingly also on line one, right? yeahinterestingly, also on
    line one??


