FROM python:3.7-slim-buster

MAINTAINER Strateos <engineering@strateos.com>

# Default userid=1000 as that is the first non-root userid on linux
ARG NB_UID=1000
ARG NB_USER=txpy

# Dependencies for scientific libraries
RUN apt-get update --fix-missing && \
    apt-get install -y \
	pkg-config \
        libjpeg-dev \
        zlib1g-dev \
	libblas-dev \
	liblapack-dev \
	gfortran \
	wget \
	git \
	&& \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


# Change default install directory of pip and eggs
RUN mkdir /pip_cache && \
    mkdir /python_eggs
ENV XDG_CONFIG_HOME /pip_cache
ENV PYTHON_EGG_CACHE /python_eggs

# Install Jupyter, nbgitpuller for separate notebook/environment
RUN pip install --no-cache-dir notebook==5.* && \
    pip install nbgitpuller==1.*

# Install TxPy
RUN pip install 'transcriptic[jupyter, analysis]'

# Add user txpy with specified uid
RUN useradd -u $NB_UID -m -s /bin/bash $NB_USER
ENV HOME /home/$NB_USER
WORKDIR /home/$NB_USER

RUN chown -R $NB_USER /home/$NB_USER
USER $NB_USER

ENTRYPOINT []
