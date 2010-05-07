# monocle - An async programming framework with a blocking look-alike syntax.
By Greg Hazel and Steven Hazel.

monocle straightens out event-driven code using Python's generators.
It aims to be portable between event-driven I/O frameworks, and
currently supports Twisted and Tornado.

It's for Python 2.5 and up; the syntax it uses isn't supported
in older versions of Python.

## A Simple Example

Here's a simple monocle program that runs two concurrent lightweight
processes (called "o-routines") using Tornado's event loop:

    import monocle
    monocle.init("tornado")
    from monocle.stack import eventloop
    from monocle.util import sleep

    @monocle.o
    def seconds():
        while True:
            yield sleep(1)
            print "1"

    @monocle.o
    def minutes():
        while True:
            yield sleep(60)
            print "60"
	    
    monocle.launch(seconds)
    monocle.launch(minutes)
    eventloop.run()

## @_o

It's important that code be dapper and well-dressed, so if you prefer,
you can don the monocle and use this handy shortcut for monocle.o:

    from monocle import _o

    @_o
    def seconds():
        while True:
            yield sleep(1)
            print "1"

It's true, this violates Python's convention that underscores indicate
variables for internal use.  But rules are for breaking.  Live a
little.

## The Big Idea

Event-driven code can be efficient and easy to reason about, but it
often splits up procedures in an unpleasant way.  Here's an example of
a blocking function to read a request from a user, query a database,
and return a result:

    def do_cmd(conn):
        cmd = conn.read_until("\n")
	if cmd.type == "get-address":
            user = db.query(cmd.username)
            conn.write(user.address)
        else:
            conn.write("unknown command")

Here's the same thing in event-driven style, using callbacks:

    def handle_cmd(conn, cmd):
        if cmd.type == "get-address":
	    # keep track of the conn so we can write the response back!
            def callback(result):
                handle_user_query_result(conn, result)
            db.query(cmd.username, callback)
        else:
            conn.write("unknown command")

    def handle_user_query_result(conn, user):
        conn.write(user.address)

What started out as a single function in the blocking code has
expanded here into three functions (counting the `callback` closure
that captures `conn`).  In real event-driven code, this kind of thing
happens a *lot*.  Any time we want to do I/O, we have to register a
new handler and return back out to the event loop to let other things
happen while we wait for the I/O to finish.  It would be nice if we
had some way to tell the event loop to call back into the *middle* of
our function, so we could just continue where we left off.

Fortunately, Python has a mechanism that lets us do exactly that,
called generators.  Monocle uses generators to straighten out
event-driven code.

Here's the monocle equivalent of the event-based code above:

    @_o
    def do_cmd(conn):
        cmd = yield conn.read_until("\n")
	if cmd.type == "get-address":
            user = yield db.query(cmd.username)
            yield conn.write(user.address)
        else:
            yield conn.write("unknown command")

It's event-driven for efficient concurrency, but otherwise looks a lot
like the original blocking code.  The resulting approach is a kind of
cooperative concurrency that makes for simpler code than
callback-based event-driven code, but which we think is easier to
reason about than multi-threaded code.

## Related Work
monocle is similar to, and takes inspiration from:

 * Twisted's inlineCallbacks
 * BTL's yielddefer
 * diesel
 * Go's goroutines (and CSP generally)
