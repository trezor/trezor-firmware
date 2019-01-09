# initialize from the image

FROM debian:9

ARG TOOLCHAIN_FLAVOR=linux
ENV TOOLCHAIN_FLAVOR=$TOOLCHAIN_FLAVOR

# install build tools and dependencies

RUN apt-get update && apt-get install -y \
    build-essential wget git python3-pip gcc-multilib

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

# install additional tools

RUN apt-get install -y protobuf-compiler libprotobuf-dev

# setup toolchain

ENV PATH=/opt/$TOOLCHAIN_LONGVER/bin:$PATH

# install python dependencies

RUN pip3 install scons trezor

# workarounds for weird default install

RUN ln -s python3 /usr/bin/python
RUN ln -s dist-packages /usr/local/lib/python3.5/site-packages
ENV LC_ALL=C.UTF-8 LANG=C.UTF-8
