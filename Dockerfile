# initialize from the image

FROM ubuntu:14.04

# add and update package repositories

RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys FE324A81C208C89497EFC6246D1D8367A3421AFB && echo "deb http://ppa.launchpad.net/terry.guo/gcc-arm-embedded/ubuntu trusty main" >> /etc/apt/sources.list && apt-get update

# install build tools and dependencies

ENV GCC_ARM_VERSION 4.9.3.2014q4-0trusty12
RUN apt-get install -y build-essential git gcc-arm-none-eabi=$GCC_ARM_VERSION python

# clone the source code

RUN git clone https://github.com/libopencm3/libopencm3 && git clone https://github.com/trezor/trezor-mcu

# build libopencm3

ENV LIBOPENCM3_GITREV 8a15cec6bf99f59065879a14895fb8af8a8a53e7
RUN cd libopencm3 && git checkout $LIBOPENCM3_GITREV && make

# build the firmware

ENV TREZOR_MCU_GITREV v1.3.0
RUN cd trezor-mcu && git checkout $TREZOR_MCU_GITREV && git submodule update --init && make && cd firmware && make
