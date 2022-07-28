FROM gcr.io/oss-fuzz-base/base-builder
RUN apt-get update && apt-get install -y make autoconf automake libtool \
  pkg-config
COPY . $SRC/trezor-firmware
WORKDIR $SRC/trezor-firmware/crypto
COPY .clusterfuzzlite/build.sh $SRC/
