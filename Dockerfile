# initialize from the image

FROM debian:9

# install build tools and dependencies

RUN apt-get update && \
    apt-get install -y \
    build-essential curl unzip git python3 python3-pip gcc-arm-none-eabi libnewlib-arm-none-eabi

ENV PROTOBUF_VERSION=3.4.0
RUN curl -LO "https://github.com/google/protobuf/releases/download/v${PROTOBUF_VERSION}/protoc-${PROTOBUF_VERSION}-linux-x86_64.zip"

# use zipfile module to extract files world-readable
RUN python3 -m zipfile -e "protoc-${PROTOBUF_VERSION}-linux-x86_64.zip" /usr/local && chmod 755 /usr/local/bin/protoc

RUN pip3 install pipenv


RUN ln -s python3 /usr/bin/python
