# initialize from the image

FROM debian:9

# install build tools and dependencies

RUN apt-get update && \
    apt-get install -y \
    build-essential curl unzip git python3 python3-pip \
    gcc-arm-none-eabi libnewlib-arm-none-eabi

ENV PROTOBUF_VERSION=3.4.0
RUN curl -LO "https://github.com/google/protobuf/releases/download/v${PROTOBUF_VERSION}/protoc-${PROTOBUF_VERSION}-linux-x86_64.zip"

ENV PYTHON=python3

# use zipfile module to extract files world-readable
RUN $PYTHON -m zipfile -e "protoc-${PROTOBUF_VERSION}-linux-x86_64.zip" /usr/local && chmod 755 /usr/local/bin/protoc

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

ENV WORKON_HOME=/tmp/.venvs

RUN $PYTHON -m pip install pipenv
