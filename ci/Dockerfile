# initialize from the image

FROM python

ARG TOOLCHAIN_FLAVOR=linux
ENV TOOLCHAIN_FLAVOR=$TOOLCHAIN_FLAVOR

# install build tools and dependencies

RUN apt-get update && apt-get install -y \
    build-essential wget git libsodium-dev graphviz \
    valgrind check libssl-dev libusb-1.0-0-dev libudev-dev

# TODO are all apt packages actually needed?

# install dependencies from toolchain source build

RUN if [ "$TOOLCHAIN_FLAVOR" = "src" ]; then \
        apt-get install -y autoconf autogen bison dejagnu \
                           flex flip gawk git gperf gzip nsis \
                           openssh-client p7zip-full perl python-dev \
                           libisl-dev tcl tofrodos zip \
                           texinfo texlive texlive-extra-utils; \
    fi

# download toolchain

ENV TOOLCHAIN_SHORTVER=8-2018q4
ENV TOOLCHAIN_LONGVER=gcc-arm-none-eabi-8-2018-q4-major
ENV TOOLCHAIN_URL=https://developer.arm.com/-/media/Files/downloads/gnu-rm/$TOOLCHAIN_SHORTVER/$TOOLCHAIN_LONGVER-$TOOLCHAIN_FLAVOR.tar.bz2
ENV TOOLCHAIN_HASH_linux=fb31fbdfe08406ece43eef5df623c0b2deb8b53e405e2c878300f7a1f303ee52
ENV TOOLCHAIN_HASH_src=bc228325dbbfaf643f2ee5d19e01d8b1873fcb9c31781b5e1355d40a68704ce7

# extract toolchain

RUN cd /opt && wget $TOOLCHAIN_URL

RUN cd /opt && echo "$TOOLCHAIN_HASH_linux $TOOLCHAIN_LONGVER-linux.tar.bz2\n$TOOLCHAIN_HASH_src $TOOLCHAIN_LONGVER-src.tar.bz2" | sha256sum -c --ignore-missing

RUN cd /opt && tar xfj $TOOLCHAIN_LONGVER-$TOOLCHAIN_FLAVOR.tar.bz2

# build toolchain (if required)

RUN if [ "$TOOLCHAIN_FLAVOR" = "src" ]; then \
        pushd /opt/$TOOLCHAIN_LONGVER ; \
        ./install-sources.sh --skip_steps=mingw32 ; \
        ./build-prerequisites.sh --skip_steps=mingw32 ; \
        ./build-toolchain.sh --skip_steps=mingw32,manual ; \
        popd ; \
    fi

# download protobuf

ENV PROTOBUF_VERSION=3.4.0
ENV PROTOBUF_HASH=e4b51de1b75813e62d6ecdde582efa798586e09b5beaebfb866ae7c9eaadace4
RUN wget "https://github.com/google/protobuf/releases/download/v${PROTOBUF_VERSION}/protoc-${PROTOBUF_VERSION}-linux-x86_64.zip"
RUN echo "${PROTOBUF_HASH} protoc-${PROTOBUF_VERSION}-linux-x86_64.zip" | sha256sum -c

# setup toolchain

ENV PATH=/opt/$TOOLCHAIN_LONGVER/bin:$PATH

ENV LC_ALL=C.UTF-8 LANG=C.UTF-8

# use zipfile module to extract files world-readable
ENV PYTHON=python

RUN $PYTHON -m zipfile -e "protoc-${PROTOBUF_VERSION}-linux-x86_64.zip" /usr/local && chmod 755 /usr/local/bin/protoc

ENV WORKON_HOME=/tmp/.venvs

# install python dependencies

RUN pip install pipenv

RUN $PYTHON --version
RUN pip --version
RUN pipenv --version
