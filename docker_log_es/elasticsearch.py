#!/usr/bin/env python
# encoding: utf-8
import struct
from datetime import datetime
from ujson import dumps
from tornado.gen import coroutine, sleep
from tornado.ioloop import IOLoop
from tornado.httpclient import HTTPRequest
from tornado.log import app_log as log
from .storage import Storage


class ElasticStreamer(object):
    QUEUES = set([])

    def __init__(self):
        self.io_loop = IOLoop.current()
        self.io_loop.add_callback(self.flush)

    @coroutine
    def flush(self):
        while True:
            try:
                body = ''
                for q in list(self.QUEUES):
                    data = yield q.fetch()
                    for line in data:
                        opts, data = line
                        body += opts
                        body += '\n'
                        body += data
                        body += '\n'

                if not body:
                    continue

                url = "%s/_bulk" % Storage.ELASTICSEARCH
                req = HTTPRequest(method='POST', body=body, url=url)
                yield Storage.http.fetch(request=req)
            except Exception as e:
                log.exception(e)
            finally:
                yield sleep(1)


class Queue(object):
    def __init__(self, container, name, filter_func):
        self.container = container
        self.name = name
        self.filter = filter_func
        self.__buff = ''
        self.__queue = []
        self.io_loop = IOLoop.current()
        self.io_loop.add_callback(ElasticStreamer.QUEUES.add, self)
        self._closed = False

    @classmethod
    def get_index_name(cls):
        return datetime.now().strftime('docker-%Y.%m.%d')

    def __call__(self, data):
        self.__buff += data

    def close(self):
        if self._closed:
            return

        self._closed = True
        IOLoop.instance().call_later(3, ElasticStreamer.QUEUES.remove, self)

    def parse_header(self, data):
        lst = struct.unpack('>4b I', data)
        return lst[0], lst[-1]

    STREAMS = ('stdin', 'stdout', 'stderr')

    @coroutine
    def fetch(self):
        q = list()
        while len(self.__buff) > 8:
            header, self.__buff = self.__buff[:8], self.__buff[8:]
            stream, length = self.parse_header(header)

            if len(self.__buff) < length:
                continue

            message, self.__buff = self.__buff[:length], self.__buff[length:]

            ts, message = message.split(' ', 1)

            msg = {'stream': self.STREAMS[stream], 'timestamp': ts.lstrip('[').rstrip(']')}
            msg.update(self.filter(message))

            q.append((
                dumps({
                    'index': {
                        '_index': self.get_index_name(),
                        '_type': self.name
                    }
                }),
                dumps(msg)
            ))

        return q
