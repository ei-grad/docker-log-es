#!/usr/bin/env python
# encoding: utf-8
import os
from setuptools import setup, find_packages


scripts = filter(
    lambda x: os.access(x, os.X_OK),
    [os.path.join('bin', i) for i in os.listdir("bin") if os.path.isfile(os.path.join('bin', i))]
)


setup(
    name='docker-log-es',
    scripts=scripts,
    version='0.0.1',
    description='Pushing Docker logs to elasticsearch',
    author='Andrew Grigoriev, Dmitry Orlov',
    author_email='andrew@ei-grad.ru, me@mosquito.su',
    url='https://github.com/ei-grad/docker-log-es',
    packages=find_packages(),
    install_requires=(
        'tornado',
        'ujson',
    )
)