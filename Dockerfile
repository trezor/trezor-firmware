# initialize from the image

FROM ubuntu:14.04

# update repositories

RUN apt-get update

# install build tools and dependencies

RUN apt-get install -y build-essential git python gcc-arm-none-eabi
