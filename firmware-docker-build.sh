#!/bin/bash
IMAGETAG=trezor-mcu-build
FIRMWARETAG=v1.3.0

docker build -t $IMAGETAG .
docker run -t -v $(pwd):/output $IMAGETAG /bin/sh -c "\
	git clone https://github.com/trezor/trezor-mcu && \
	cd trezor-mcu && \
	git checkout $FIRMWARETAG && \
	git submodule update --init && \
	make && \
	cd firmware && \
	make && \
	cp trezor.bin /output \
	"

echo "---------------------"
echo "Firmware fingerprint:"

sha256sum trezor.bin
