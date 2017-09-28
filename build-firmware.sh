#!/bin/bash
set -e

IMAGE=trezor-mcu-build
TAG=${1:-master}
BINFILE=build/trezor-$TAG.bin
ELFFILE=build/trezor-$TAG.elf

docker build -t $IMAGE .
docker run -t -v $(pwd)/build:/build:z $IMAGE /bin/sh -c "\
	git clone https://github.com/trezor/trezor-mcu && \
	cd trezor-mcu && \
	git checkout $TAG && \
	git submodule update --init && \
	make -C vendor/libopencm3 && \
	make -C vendor/nanopb/generator/proto && \
	make -C firmware/protob && \
	make && \
	make -C firmware sign && \
	cp firmware/trezor.bin /$BINFILE && \
	cp firmware/trezor.elf /$ELFFILE"

/usr/bin/env python -c "
from __future__ import print_function
import hashlib
import sys
fn = sys.argv[1]
data = open(fn, 'rb').read()
print('\n\n')
print('Filename    :', fn)
print('Fingerprint :', hashlib.sha256(data[256:]).hexdigest())
print('Size        : %d bytes (out of %d maximum)' % (len(data), 491520))
" $BINFILE
