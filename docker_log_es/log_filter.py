#!/usr/bin/env python
# encoding: utf-8

from collections import defaultdict
from types import GeneratorType
from functools import wraps
import re

from tornado.log import app_log as log

import yaml

from docker_log_es.utils import b

iteritems = lambda x: getattr(x, 'iteritems', x.items)()


def coroutine(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        g = func(*args, **kwargs)
        assert isinstance(g, GeneratorType)
        g.next()
        return g
    return wrap


def build_filters(names, images):
    def try_to_parse(msg, exp):
        m = exp.match(msg)
        if m:
            return m.groupdict()
        else:
            return {'message': msg}

    def update_from_subparsers(subparsers, msg):
        for field in list(msg.keys()):
            try:
                parsers = subparsers.get(field)
                if parsers:
                    data = msg[field]
                    for matcher, parser in parsers:
                        if matcher.match(data):
                            u = parser.match(data)
                            if u:
                                msg.update(u.groupdict())

            except Exception as e:
                log.exception(e)

        return msg

    def find_exp(container):
        for name, cfg in iteritems(names):
            exp, subparsers, ignore, multiline = cfg
            if name in container.name:
                return exp, multiline, subparsers, ignore

        for image, cfg in iteritems(images):
            exp, subparsers, ignore, multiline = cfg
            if image in container.image:
                return exp, multiline, subparsers, ignore

    @coroutine
    def on_message(container):
        cfg = find_exp(container)
        if cfg:
            exp, multiline, subparsers, ignore = cfg
        else:
            exp, multiline, subparsers, ignore = None, False, None, False

        result = None
        buff = b('')
        while True:
            message = (yield result)
            if ignore:
                result = False
                continue

            if multiline:
                if multiline.match(message):
                    if buff:
                        if exp:
                            result = try_to_parse(buff, exp)
                        else:
                            result = {"message": buff}

                        buff = message
                        if subparsers:
                            result = update_from_subparsers(subparsers, result)
                    else:
                        buff += message
                        result = False
                elif buff:
                    result = False
                    buff += message
            else:
                if exp:
                    message = try_to_parse(message, exp)
                if subparsers:
                    message = update_from_subparsers(subparsers, message)
                result = {"message": message}

    return on_message


def yml_filter(fd=None):
    if fd:
        config = yaml.load(fd)
        names = {}
        images = {}

        for _filter, _cfg in config.items():
            exp = b(_cfg.get('exp', None))
            if exp:
                exp = re.compile(exp)

            subparsers = defaultdict(set)

            for field, parsers in iteritems(_cfg.get('subparsers', {})):
                for matcher, parser in iteritems(parsers):
                    subparsers[field].add((re.compile(b(matcher)), re.compile(b(parser))))

            name = _cfg.get('name')
            image = _cfg.get('image')
            ignore = _cfg.get('ignore', False)
            multiline = _cfg.get('multiline', False)
            multiline = re.compile(multiline) if multiline else False

            if name:
                names[name] = (exp, subparsers, ignore, multiline)

            if image:
                images[image] = (exp, subparsers, ignore, multiline)

        return build_filters(names, images)
    else:
        return no_filter
