#!/usr/bin/env python
# encoding: utf-8

from collections import defaultdict
import re

from tornado.log import app_log as log

import yaml

from docker_log_es.utils import b


no_filter = lambda x, c: {"message": str(x)}
iteritems = lambda x: getattr(x, 'iteritems', x.items)()


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

    def on_message(message, container):
        for name, cfg in iteritems(names):
            exp, subparsers = cfg
            if name in container.name:
                return update_from_subparsers(subparsers, try_to_parse(message, exp))

        for image, cfg in iteritems(images):
            exp, subparsers = cfg
            if image in container.image:
                return update_from_subparsers(subparsers, try_to_parse(message, exp))

        return no_filter(message, container)

    return on_message


def yml_filter(fd=None):
    if fd:
        config = yaml.load(fd)
        names = {}
        images = {}
        for _filter, _cfg in config.items():
            exp = re.compile(b(_cfg['exp']))
            subparsers = defaultdict(set)

            for field, parsers in iteritems(_cfg.get('subparsers', {})):
                for matcher, parser in iteritems(parsers):
                    subparsers[field].add((re.compile(b(matcher)), re.compile(b(parser))))

            name = _cfg.get('name')
            image = _cfg.get('image')

            if name:
                names[name] = (exp, subparsers)

            if image:
                images[image] = (exp, subparsers)

        return build_filters(names, images)
    else:
        return no_filter
