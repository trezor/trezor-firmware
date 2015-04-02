# initialize from the image

FROM ubuntu:14.04

ENV GCC_ARM_VERSION 4.9.3.2015q1-0trusty13

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

ENV LIBOPENCM3_GITREV 7dbb93c78411b37bec64b5ca5be55076b0ab1b15
RUN cd libopencm3 && git checkout $LIBOPENCM3_GITREV && make
