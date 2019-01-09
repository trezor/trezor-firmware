# initialize from the image

FROM debian:9

# install build tools and dependencies

ARG EMULATOR=0
ENV EMULATOR=$EMULATOR

RUN apt-get update && \
    apt-get install -y build-essential curl git python3 python3-pip

RUN if [ "$EMULATOR" = 1 ]; then \
        apt-get install -y libsdl2-dev libsdl2-image-dev; \
    else \
        apt-get install -y gcc-arm-none-eabi libnewlib-arm-none-eabi; \
    fi

ENV PROTOBUF_VERSION=3.4.0
ENV PROTOBUF_HASH=e4b51de1b75813e62d6ecdde582efa798586e09b5beaebfb866ae7c9eaadace4
RUN curl -LO "https://github.com/google/protobuf/releases/download/v${PROTOBUF_VERSION}/protoc-${PROTOBUF_VERSION}-linux-x86_64.zip"
RUN echo "${PROTOBUF_HASH} protoc-${PROTOBUF_VERSION}-linux-x86_64.zip" | sha256sum -c

ENV PYTHON=python3
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# use zipfile module to extract files world-readable
RUN $PYTHON -m zipfile -e "protoc-${PROTOBUF_VERSION}-linux-x86_64.zip" /usr/local && chmod 755 /usr/local/bin/protoc

ENV WORKON_HOME=/tmp/.venvs

RUN $PYTHON -m pip install pipenv
