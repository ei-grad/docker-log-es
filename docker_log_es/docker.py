#!/usr/bin/env python
# encoding: utf-8
import struct
from collections import namedtuple
from tornado.gen import coroutine, Return, sleep
from tornado.httpclient import HTTPRequest
from tornado.ioloop import IOLoop
from tornado.log import app_log as log
from .storage import Storage
from .elasticsearch import Queue
from ujson import loads


Container = namedtuple("Image", 'id name image')


class Docker(object):
    def __init__(self, filter_func=lambda x, c: {"message": str(x)}):
        self.io_loop = IOLoop.current()
        self.url = Storage.DOCKER
        self._containers = {}
        self.running = True
        self.io_loop.add_callback(self.container_updater)
        self.filter = filter_func

    @coroutine
    def container_updater(self):
        while self.running:
            containers = yield self.containers()
            current = set([])
            for name, image, cid in containers:
                current.add(Container(id=cid, name=name, image=image))

            for cnt in list(current - Storage.CONTAINERS):
                Storage.CONTAINERS.add(cnt)
                log.info('Starting logging capture for "%s"', cnt.name)
                self.io_loop.add_callback(self.do_logs, cnt, self.filter)

            for cnt in list(Storage.CONTAINERS - current):
                queue = self._containers.get(cnt)
                if queue:
                    log.info('Stopping logging for container %r', cnt)
                    queue.close()

                    self._containers.pop(cnt)
                    Storage.CONTAINERS.remove(cnt)

            yield sleep(3)

    @coroutine
    def containers(self):
        url = "%s/containers/json?all=1&status=running" % self.url
        req = HTTPRequest(url=url, method='GET')
        resp = yield Storage.http.fetch(request=req)
        containers = map(
            lambda x: (filter(lambda c: c.count('/') == 1, x['Names'])[0][1:], x['Image'], x['Id']),
            filter(lambda x: 'Up' in x['Status'], loads(resp.body))
        )
        raise Return(containers)

    @coroutine
    def do_logs(self, container, log_filter):
        url = "%s/containers/%s/logs?follow=1&tail=0&stderr=1&stdout=1&timestamps=1" % (self.url, container.id)

        q = Queue(container, log_filter)

        Storage.http.fetch(
            url,
            streaming_callback=q,
            callback=lambda r: self.on_log_callback(r, q, container),
            request_timeout=0,
        )

        self._containers[container] = q

    def on_log_callback(self, result, queue, container):
        queue.close()
        Storage.CONTAINERS.remove(container)
        self._containers.pop(container)