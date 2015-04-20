#!/usr/bin/env python
# encoding: utf-8


class RegexpCollector(object):

    def __init__(self, emit, regexp):
        self.emit = emit
        self.regexp = regexp

    def __call__(self, data):
        self.buf += data
        # TODO:
