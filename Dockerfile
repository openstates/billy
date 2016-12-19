FROM        debian:jessie
MAINTAINER  James Turk <james@openstates.org>

RUN apt-get update && apt-get install -y \
    python2.7 \
    python-pip \
    python-lxml \
    python-pymongo \
    libpq-dev \
    git \
    libgeos-dev \
    mercurial \
    imagemagick \
    jpegoptim

RUN mkdir -p /opt/openstates/
ADD . /opt/openstates/billy/
RUN pip install -r /opt/openstates/billy/requirements.txt
RUN pip install -e /opt/openstates/billy/

RUN mkdir -p /billy
WORKDIR /billy

ENV PYTHONIOENCODING 'utf-8'
ENV LANG 'en_US.UTF-8'

ENTRYPOINT ["billy-update"]
