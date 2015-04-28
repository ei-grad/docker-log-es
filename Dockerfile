FROM python:3-onbuild
MAINTAINER Andrew Grigorev <andrew@ei-grad.ru>
RUN cd /usr/src/app && pip install .
ENTRYPOINT ["docker-log-es"]
