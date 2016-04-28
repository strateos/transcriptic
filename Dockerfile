FROM debian:jessie

MAINTAINER Transcriptic <team@transcriptic.com>

RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y \
	python-dev \
	python \
	python-pip \
	python-virtualenv \
	python-setuptools \
	libfreetype6-dev \
    libpng12-0-dev \
    libjpeg-dev \
	pkg-config \
	libblas-dev \
	liblapack-dev \
	gfortran \
	wget \
	git \
	&& rm -rf /var/lib/apt/lists/*

RUN pip install -U virtualenv

RUN pip install numpy scipy pandas matplotlib pillow future

RUN pip install tox pytest

RUN useradd -ms /bin/bash txtron
ENV HOME /home/txtron
WORKDIR /home/txtron
USER root

