FROM python:3-onbuild
MAINTAINER Andrew Grigorev <andrew@ei-grad.ru>
RUN sudo apt-get install libyaml-dev
RUN cd /usr/src/app && pip install .
ENTRYPOINT ["docker-log-es"]
