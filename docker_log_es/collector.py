#!/usr/bin/env python
# encoding: utf-8


class LineCollector(object):

    def __init__(self, emit):
        self.emit = emit
        self.buf = ""

    def __call__(self, data):
        self.buf += data
        if '\n' in self.buf:
            d, self.buf = self.buf.split('\n', 1)
            self.emit(d)
