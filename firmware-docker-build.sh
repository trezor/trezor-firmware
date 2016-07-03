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
	make && \
	make -C firmware && \
	cp firmware/trezor.bin /output/trezor-$FIRMWARETAG.bin"

echo "---------------------"
echo "Firmware fingerprint:"
FILENAME=output/trezor-$FIRMWARETAG.bin
sha256sum "$FILENAME"
FILESIZE=$(stat -c%s "$FILENAME")
echo "Firmware size: $FILESIZE bytes (out of 491520 maximum)"
