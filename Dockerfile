# initialize from the image

FROM ubuntu:14.04

# update repositories

RUN apt-get update

# install build tools and dependencies

RUN apt-get install -y build-essential git python gcc-arm-none-eabi

# clone the source code

RUN git clone https://github.com/libopencm3/libopencm3

# build libopencm3

ENV LIBOPENCM3_GITREV 7b29caed1a726b5cef4c269b6a6ef7a1f1dd105c
RUN cd libopencm3 && git checkout $LIBOPENCM3_GITREV && make
