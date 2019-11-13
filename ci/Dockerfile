# initialize from the image

FROM debian:10

ARG TOOLCHAIN_FLAVOR=linux
ENV TOOLCHAIN_FLAVOR=${TOOLCHAIN_FLAVOR}

ARG FULLDEPS_TESTING=0
ENV FULLDEPS_TESTING=${FULLDEPS_TESTING}

# install build tools and dependencies

RUN apt-get update && apt-get install -y \
        build-essential \
        check \
        clang-format \
        git \
        graphviz \
        libjpeg-dev \
        libsdl2-dev \
        libsdl2-image-dev \
        libsodium-dev \
        libssl-dev \
        libudev-dev \
        libusb-1.0-0-dev \
        valgrind \
        wget \
        zlib1g-dev

# install python 3.7.3 + pip from the image

RUN apt-get install -y \
    python3-dev \
    python3-pip

# install other python versions from their sources

RUN if [ "${FULLDEPS_TESTING}" = "1" ]; then \
        export PYTHON35VER="3.5.7" ; \
        wget --no-verbose https://www.python.org/ftp/python/${PYTHON35VER}/Python-${PYTHON35VER}.tgz ; \
        tar zxf Python-${PYTHON35VER}.tgz ; \
        cd Python-${PYTHON35VER}/ && ./configure && make && make install ; \
    fi

RUN if [ "${FULLDEPS_TESTING}" = "1" ]; then \
        export PYTHON36VER="3.6.9" ; \
        wget --no-verbose https://www.python.org/ftp/python/${PYTHON36VER}/Python-${PYTHON36VER}.tgz ; \
        tar zxf Python-${PYTHON36VER}.tgz ; \
        cd Python-${PYTHON36VER}/ && ./configure && make && make install ; \
    fi

RUN if [ "${FULLDEPS_TESTING}" = "1" ]; then \
        export PYTHON38VER="3.8.0" ; \
        export PYTHONSUBVER="b3"; \
        wget --no-verbose https://www.python.org/ftp/python/${PYTHON38VER}/Python-${PYTHON38VER}${PYTHONSUBVER}.tgz ; \
        tar zxf Python-${PYTHON38VER}${PYTHONSUBVER}.tgz ; \
        cd Python-${PYTHON38VER}${PYTHONSUBVER}/ && ./configure && make && make install ; \
    fi

# install dependencies from toolchain source build

RUN if [ "${TOOLCHAIN_FLAVOR}" = "src" ]; then \
        apt-get install -y autoconf autogen bison dejagnu \
                           flex flip gawk git gperf gzip nsis \
                           openssh-client p7zip-full perl python-dev \
                           libisl-dev tcl tofrodos zip \
                           texinfo texlive texlive-extra-utils; \
    fi

# download toolchain

ENV TOOLCHAIN_LONGVER=gcc-arm-none-eabi-8-2019-q3-update
ENV TOOLCHAIN_SUBDIR="8-2019q3/RC1.1"
ENV TOOLCHAIN_URL=https://developer.arm.com/-/media/Files/downloads/gnu-rm/${TOOLCHAIN_SUBDIR}/${TOOLCHAIN_LONGVER}-${TOOLCHAIN_FLAVOR}.tar.bz2
ENV TOOLCHAIN_HASH_linux=b50b02b0a16e5aad8620e9d7c31110ef285c1dde28980b1a9448b764d77d8f92
ENV TOOLCHAIN_HASH_src=e8a8ddfec47601f2d83f1d80c0600f198476f227102121c8d6a5a781d0c2eeef

# extract toolchain

RUN cd /opt && wget --no-verbose ${TOOLCHAIN_URL}
RUN cd /opt && echo "${TOOLCHAIN_HASH_linux} ${TOOLCHAIN_LONGVER}-linux.tar.bz2\n${TOOLCHAIN_HASH_src} ${TOOLCHAIN_LONGVER}-src.tar.bz2" | sha256sum -c --ignore-missing
RUN cd /opt && tar xfj ${TOOLCHAIN_LONGVER}-${TOOLCHAIN_FLAVOR}.tar.bz2

# build toolchain (if required)

RUN if [ "${TOOLCHAIN_FLAVOR}" = "src" ]; then \
        pushd /opt/${TOOLCHAIN_LONGVER} ; \
        ./install-sources.sh --skip_steps=mingw32 ; \
        ./build-prerequisites.sh --skip_steps=mingw32 ; \
        ./build-toolchain.sh --skip_steps=mingw32,manual ; \
        popd ; \
    fi

# download protobuf

ENV PROTOBUF_VERSION=3.6.1
ENV PROTOBUF_HASH=6003de742ea3fcf703cfec1cd4a3380fd143081a2eb0e559065563496af27807
RUN wget --no-verbose "https://github.com/google/protobuf/releases/download/v${PROTOBUF_VERSION}/protoc-${PROTOBUF_VERSION}-linux-x86_64.zip"
RUN echo "${PROTOBUF_HASH} protoc-${PROTOBUF_VERSION}-linux-x86_64.zip" | sha256sum -c

# setup toolchain

ENV PATH=/opt/${TOOLCHAIN_LONGVER}/bin:${PATH}

ENV LC_ALL=C.UTF-8 LANG=C.UTF-8

ENV PYTHON=python3

# use zipfile module to extract files world-readable
RUN ${PYTHON} -m zipfile -e "protoc-${PROTOBUF_VERSION}-linux-x86_64.zip" /usr/local && chmod 755 /usr/local/bin/protoc

ENV WORKON_HOME=/tmp/.venvs

# download monero tests binary

ENV TREZOR_MONERO_TESTS_SHA256SUM=36852ff2add3f865dbf4e23f4e32e1022a8f4b14cd4fb4eb97491d99ba93b9bc
ENV TREZOR_MONERO_TESTS_URL="https://github.com/ph4r05/monero/releases/download/v0.15.0.0-tests-u18.04-02/trezor_tests"
ENV TREZOR_MONERO_TESTS_PATH="/opt/trezor_monero_tests"

RUN if [ "${FULLDEPS_TESTING}" = "1" ]; then \
        wget --no-verbose "${TREZOR_MONERO_TESTS_URL}" -O "${TREZOR_MONERO_TESTS_PATH}" ; \
        chmod +x "${TREZOR_MONERO_TESTS_PATH}" ; \
        echo "${TREZOR_MONERO_TESTS_SHA256SUM} ${TREZOR_MONERO_TESTS_PATH}" | sha256sum -c ; \
    fi

# install python dependencies

RUN ${PYTHON} -m pip install pipenv

RUN ${PYTHON} --version
RUN ${PYTHON} -m pip --version
RUN pipenv --version
