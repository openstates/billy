FROM        debian:jessie
MAINTAINER  Paul R. Tagliamonte <paultag@sunlightfoundation.com>

RUN apt-get update && apt-get install -y \
    python2.7 python-pip python-lxml python-pymongo libpq-dev git libgeos-dev mercurial

RUN mkdir -p /opt/sunlightfoundation.com/
ADD . /opt/sunlightfoundation.com/billy/
RUN pip install -r /opt/sunlightfoundation.com/billy/requirements.txt
RUN pip install -e /opt/sunlightfoundation.com/billy/

RUN mkdir -p /billy
WORKDIR /billy

ENTRYPOINT ["billy-update"]
