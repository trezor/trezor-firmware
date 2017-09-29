# initialize from the image

FROM debian:9

# install build tools and dependencies

RUN apt-get update && apt-get install -y \
    build-essential git python python-ecdsa gcc-arm-none-eabi \
    protobuf-compiler libprotobuf-dev python-protobuf
