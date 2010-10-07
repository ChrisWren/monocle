# -*- coding: utf-8 -*-
#
# by Steven Hazel

import errno
import socket

import tornado.ioloop
from tornado.iostream import IOStream

from monocle import _o, launch
from monocle.deferred import Deferred
from monocle.stack.network import Connection as BaseConnection
from monocle.stack.network import ConnectionLost
from monocle.tornado_stack.eventloop import evlp


class _Connection(IOStream):

    def attach(self, connection):
        self.set_close_callback(self._close_called)
        self._write_flushed = connection._write_flushed
        self._closed = connection._closed
        self.drd = None
        self.connect_df = Deferred()

    def read(self, size):
        df = Deferred()
        self.drd = df
        IOStream.read_bytes(self, size, self._read_complete)
        return df

    def read_until(self, s):
        df = Deferred()
        self.drd = df
        IOStream.read_until(self, s, self._read_complete)
        return df

    def _read_complete(self, result):
        df = self.drd
        self.drd = None
        df.callback(result)

    def _handle_connect(self, reason=None):
        df = self.connect_df
        self.connect_df = None
        df.callback(reason)

    def _handle_events(self, fd, events):
        if self.connect_df:
            self._handle_connect(None)
        IOStream._handle_events(self, fd, events)

    def _close_called(self, reason=None):
        # XXX: get a real reason from Tornado
        if reason is None:
            reason = IOError("Connection closed")
        if self.connect_df is not None:
            self._handle_connect(reason)
        self._closed(reason)

    # functions to support the StackConnection interface

    def write(self, data):
        IOStream.write(self, data, self._write_flushed)

    def disconnect(self):
        self.close()


class Connection(BaseConnection):

    def read(self, size):
        self._check_reading()
        return self._stack_conn.read(size)

    def read_until(self, s):
        self._check_reading()
        return self._stack_conn.read_until(s)


class Service(object):
    def __init__(self, handler, port, bindaddr="", backlog=128):
        @_o
        def _handler(s):
            try:
                yield launch(handler(s))
            finally:
                s.close()
        self.handler = _handler
        self.port = port
        self.bindaddr = bindaddr
        self.backlog = backlog
        self._sock = socket.socket()
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.setblocking(0)
        self._sock.bind((self.bindaddr, self.port))
        self._sock.listen(self.backlog)

    def _connection_ready(self, fd, events):
        while True:
            try:
                s, address = self._sock.accept()
            except socket.error, e:
                if e[0] not in (errno.EWOULDBLOCK, errno.EAGAIN):
                    raise
                return
            s.setblocking(0)
            connection = Connection(_Connection(s))
            connection._stack_conn.attach(connection)
            self.handler(connection)

    def _add(self, evlp):
        evlp._add_handler(self._sock.fileno(),
                          self._connection_ready,
                          evlp.READ)


class Client(Connection):
    @_o
    def connect(self, host, port):
        s = socket.socket()
        self._stack_conn = _Connection(s)
        self._stack_conn.attach(self)

        err = s.connect_ex((host, port))
        if err in (errno.EINPROGRESS, errno.EALREADY, errno.EWOULDBLOCK):
            self._stack_conn._add_io_state(self._stack_conn.io_loop.READ)
            self._stack_conn._add_io_state(self._stack_conn.io_loop.WRITE)
            yield self._stack_conn.connect_df
        elif err not in (0, errno.EISCONN):
            raise socket.error(err, errorcode[err])


def add_service(service, evlp=evlp):
    return service._add(evlp)
