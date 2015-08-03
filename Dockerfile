# initialize from the image

FROM ubuntu:14.04

ENV GCC_ARM_VERSION 4.9.3.2015q2-1trusty1

# add and update package repositories

RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys FE324A81C208C89497EFC6246D1D8367A3421AFB
RUN gpg --keyring /etc/apt/trusted.gpg --primary-keyring /etc/apt/trusted.gpg --fingerprint FE324A81C208C89497EFC6246D1D8367A3421AFB
RUN echo "deb http://ppa.launchpad.net/terry.guo/gcc-arm-embedded/ubuntu trusty main" >> /etc/apt/sources.list && apt-get update

# install build tools and dependencies

RUN apt-get install -y build-essential git python
RUN apt-get install -y gcc-arm-none-eabi=$GCC_ARM_VERSION

# clone the source code

RUN git clone https://github.com/libopencm3/libopencm3

# build libopencm3

ENV LIBOPENCM3_GITREV 7b29caed1a726b5cef4c269b6a6ef7a1f1dd105c
RUN cd libopencm3 && git checkout $LIBOPENCM3_GITREV && make
