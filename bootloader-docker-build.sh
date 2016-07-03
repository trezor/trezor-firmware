#!/bin/bash
set -e

IMAGETAG=trezor-mcu-build
FIRMWARETAG=${1:-master}

docker build -t $IMAGETAG .
docker run -t -v $(pwd)/output:/output $IMAGETAG /bin/sh -c "\
	git clone https://github.com/trezor/trezor-mcu && \
	cd trezor-mcu && \
	git checkout $FIRMWARETAG && \
	git submodule update --init && \
	make -C vendor/libopencm3 && \
	export OPTFLAGS=-Os
	make && \
	make -C bootloader && \
	cp bootloader/bootloader.bin /output/bootloader-$FIRMWARETAG.bin"

echo "---------------------"
echo "Bootloader fingerprint:"
FILENAME=output/bootloader-$FIRMWARETAG.bin
sha256sum "$FILENAME"
FILESIZE=$(stat -c%s "$FILENAME")
echo "Bootloader size: $FILESIZE bytes (out of 32768 maximum)"
