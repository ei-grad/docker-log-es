#!/usr/bin/env python
# encoding: utf-8
import os
from setuptools import setup, find_packages


scripts = [x for x in [
    os.path.join('bin', i)
    for i in os.listdir("bin")
    if os.path.isfile(os.path.join('bin', i))
] if os.access(x, os.X_OK)]


setup(
    name='docker-log-es',
    scripts=scripts,
    version='0.0.1',
    description='Put Docker logs to ElasticSearch',
    author='Andrew Grigoriev, Dmitry Orlov',
    author_email='andrew@ei-grad.ru, me@mosquito.su',
    url='https://github.com/ei-grad/docker-log-es',
    packages=find_packages(),
    install_requires=['tornado', 'elasticsearch', 'ujson'],
)
