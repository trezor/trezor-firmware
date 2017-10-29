# initialize from the image

FROM debian:9

# install build tools and dependencies

RUN apt-get update && apt-get install -y \
    build-essential git python python-ecdsa gcc-arm-none-eabi curl
RUN apt-get install -y unzip python-pip

ENV PROTOBUF_VERSION=3.4.0
RUN curl -LO "https://github.com/google/protobuf/releases/download/v${PROTOBUF_VERSION}/protoc-${PROTOBUF_VERSION}-linux-x86_64.zip"
RUN unzip "protoc-${PROTOBUF_VERSION}-linux-x86_64.zip" -d /usr
RUN pip2 install "protobuf==${PROTOBUF_VERSION}"
