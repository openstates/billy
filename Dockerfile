FROM        sunlightlabs/pupa:latest
MAINTAINER  Paul R. Tagliamonte <paultag@sunlightfoundation.com>

RUN mkdir -p /opt/sunlightfoundation.com/
ADD . /opt/sunlightfoundation.com/scrapers-us-state/
RUN echo "deb-src http://http.debian.net/debian/ unstable main" >> /etc/apt/sources.list
RUN apt-get update && apt-get build-dep python3-lxml -y
RUN pip3 install lxml python-dateutil

RUN echo "/opt/sunlightfoundation.com/scrapers-us-state/" > /usr/lib/python3/dist-packages/scrapers-us-state.pth
