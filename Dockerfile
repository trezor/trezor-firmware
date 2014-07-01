# initialize from the image

FROM ubuntu:14.04

# add and update package repositories

RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys FE324A81C208C89497EFC6246D1D8367A3421AFB && echo "deb http://ppa.launchpad.net/terry.guo/gcc-arm-embedded/ubuntu trusty main" >> /etc/apt/sources.list && apt-get update

# define used versions for pinning

ENV GCC_ARM_VERSION    4-8-2014q2-0trusty10
ENV LIBOPENCM3_GITREV  f6b6d62ec5628ebb0602c466ee9fd7a6070ef1f0
ENV TREZOR_MCU_GITREV  v1.2.0

# install build tools and dependencies

RUN apt-get install -y build-essential git gcc-arm-none-eabi=$GCC_ARM_VERSION python

# clone the source code

RUN git clone https://github.com/libopencm3/libopencm3 && git clone https://github.com/trezor/trezor-mcu

# build libopencm3

RUN cd libopencm3 && git checkout $LIBOPENCM3_GITREV && make

# build the firmware

RUN cd trezor-mcu && git checkout $TREZOR_MCU_GITREV && git submodule update --init && make && cd firmware && make
