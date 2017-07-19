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
	CFLAGS='-std=c99' make -C vendor/libopencm3 && \
	make && \
	make -C bootloader align && \
	cp bootloader/bootloader.bin /output/bootloader-$FIRMWARETAG.bin"

echo "---------------------"
echo "Bootloader fingerprint:"
FILENAME=output/bootloader-$FIRMWARETAG.bin
/usr/bin/env python -c "import hashlib ; print(hashlib.sha256(hashlib.sha256(open('$FILENAME', 'rb').read()).digest()).hexdigest())"
FILESIZE=$(stat -c%s "$FILENAME")
echo "Bootloader size: $FILESIZE bytes (out of 32768 maximum)"
