#!/usr/bin/env python
# encoding: utf-8

from datetime import datetime
import struct

from ujson import dumps

from tornado.gen import coroutine, sleep
from tornado.ioloop import IOLoop
from tornado.httpclient import HTTPRequest
from tornado.log import app_log as log

from docker_log_es.log_filter import multiline_flag
from docker_log_es.storage import Storage
from docker_log_es.utils import b


class ElasticStreamer(object):
    QUEUES = set([])

    def __init__(self):
        self.io_loop = IOLoop.current()
        self.io_loop.add_callback(self.flush)

    @coroutine
    def flush(self):
        while True:
            try:
                body = []
                for q in list(self.QUEUES):
                    data = yield q.fetch()
                    for line in data:
                        opts, data = line
                        body.extend([opts, '\n', data, '\n'])

                body = b(''.join(body))

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
    def __init__(self, container, filter_func):
        self.container = container
        self.filter = filter_func
        self.__buff = b('')
        self.__queue = []
        self.io_loop = IOLoop.current()
        self.io_loop.add_callback(ElasticStreamer.QUEUES.add, self)
        self._closed = False

    @staticmethod
    def get_index_name():
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

    def split(self, position):
        message, self.__buff = self.__buff[:position], self.__buff[position:]
        return message

    @coroutine
    def fetch(self):
        q = list()

        on_message = self.filter(self.container)

        while len(self.__buff) > 8:
            header, self.__buff = self.__buff[:8], self.__buff[8:]
            stream, length = self.parse_header(header)

            if len(self.__buff) < length:
                continue

            if not length:
                continue

            message = self.split(length)

            ts, message = message.split(b(' '), 1)

            result = on_message.send(message)

            if result is False:
                continue

            else:
                msg = {'stream': self.STREAMS[stream], 'timestamp': ts.lstrip(b('[')).rstrip(b(']'))}
                msg.update({
                    'container': self.container.name,
                    'image': self.container.image
                })

                msg.update(result)
                log.debug(msg)
                q.append((
                    dumps({
                        'index': {
                            '_index': self.get_index_name(),
                            '_type': 'logs',
                        }
                    }),
                    dumps(msg)
                ))

        return q
