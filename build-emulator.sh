#!/bin/bash
set -e

IMAGE=trezor-mcu-build-emulator
TAG=${1:-master}
ELFFILE=build/trezor-emulator-$TAG

docker build -f Dockerfile.emulator -t $IMAGE .
docker run -t -v $(pwd)/build:/build:z $IMAGE /bin/sh -c "\
	git clone https://github.com/trezor/trezor-mcu && \
	cd trezor-mcu && \
	git checkout $TAG && \
	git submodule update --init && \
	make -C vendor/nanopb/generator/proto && \
	make -C firmware/protob && \
	EMULATOR=1 make && \
	EMULATOR=1 make -C emulator && \
	EMULATOR=1 make -C firmware && \
	cp firmware/trezor.elf /$ELFFILE"
