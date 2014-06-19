# initialize from the image

FROM ubuntu:14.04

# add and update package repositories

RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys A3421AFB && echo "deb http://ppa.launchpad.net/terry.guo/gcc-arm-embedded/ubuntu trusty main" >> /etc/apt/sources.list && apt-get update

# install build tools and dependencies

RUN apt-get install -y build-essential git gcc-arm-none-eabi python

# clone the source code

RUN git clone https://github.com/libopencm3/libopencm3 && git clone https://github.com/trezor/trezor-mcu && cd trezor-mcu && git submodule update --init

# build libopencm3

RUN cd libopencm3 && make

# build the firmware

RUN cd trezor-mcu && make && cd firmware && make
