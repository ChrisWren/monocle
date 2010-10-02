# -*- coding: utf-8 -*-
#
# by Steven Hazel

import urlparse

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

import tornado.httpclient
import tornado.httpserver

from monocle import _o, Return, VERSION, launch
from monocle.deferred import Deferred


class HttpException(Exception): pass

HttpHeaders = OrderedDict

class HttpClient(object):
    def __init__(self):
        self._proto = None

    @_o
    def request(self, url, headers=None, method='GET', body=None):
        http_client = tornado.httpclient.AsyncHTTPClient()
        req = tornado.httpclient.HTTPRequest(url,
                                             method=method,
                                             headers=headers or {},
                                             body=body)
        df = Deferred()
        http_client.fetch(req, df.callback)
        response = yield df
        yield Return(response)


class HttpServer(object):
    def __init__(self, handler, port):
        self.handler = handler
        self.port = port

    def _add(self, el):
        @_o
        def _handler(request):
            try:
                yield launch(self.handler(request))
            except:
                yield http_respond(request, 500, {},
                                   "500 Internal Server Error")
        self._http_server = tornado.httpserver.HTTPServer(
            _handler,
            io_loop=el._tornado_ioloop)
        self._http_server.listen(self.port)


@_o
def http_respond(request, code, headers, content):
    request.write("HTTP/1.1 %s\r\n" % code)
    headers['Server'] = headers.get('Server', 'monocle/%s' % VERSION)
    headers['Content-Length'] = headers.get('Content-Length', len(content))
    for name, value in headers.iteritems():
        request.write("%s: %s\r\n" % (name, value))
    request.write("\r\n")
    request.write(content)
    request.finish()
