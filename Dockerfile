# initialize from the image

FROM debian:9

# install build tools and dependencies

RUN apt-get update && apt-get install -y \
    build-essential git python3-pip \
    gcc-arm-none-eabi libnewlib-arm-none-eabi \
    gcc-multilib

RUN pip3 install click pyblake2 scons
RUN pip3 install --no-deps git+https://github.com/trezor/python-trezor.git@master

# workarounds for weird default install

RUN ln -s python3 /usr/bin/python
ENV SCONS_LIB_DIR=/usr/local/lib/python3.5/dist-packages/scons-3.0.0
ENV LC_ALL=C.UTF-8 LANG=C.UTF-8
