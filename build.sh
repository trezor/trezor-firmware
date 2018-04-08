#!/bin/bash
set -e

IMAGE=trezor-mcu-build

BOOTLOADER_TAG=${1:-master}
FIRMWARE_TAG=${2:-master}

BOOTLOADER_BINFILE=build/bootloader-$BOOTLOADER_TAG.bin
BOOTLOADER_ELFFILE=build/bootloader-$BOOTLOADER_TAG.elf

FIRMWARE_BINFILE=build/trezor-$FIRMWARE_TAG.bin
FIRMWARE_ELFFILE=build/trezor-$FIRMWARE_TAG.elf

docker build -t $IMAGE .
docker run -t -v $(pwd)/build:/build:z $IMAGE /bin/sh -c "\
	cd /tmp && \
	git clone https://github.com/trezor/trezor-mcu.git trezor-mcu-bl && \
	cd trezor-mcu-bl && \
	git checkout $BOOTLOADER_TAG && \
	git submodule update --init --recursive && \
	make -C vendor/libopencm3 && \
	make && \
	make -C bootloader align && \
	cp bootloader/bootloader.bin /$BOOTLOADER_BINFILE && \
	cp bootloader/bootloader.elf /$BOOTLOADER_ELFFILE && \
	cd /tmp && \
	git clone https://github.com/trezor/trezor-mcu.git trezor-mcu-fw && \
	cd trezor-mcu-fw && \
	git checkout $FIRMWARE_TAG && \
	git submodule update --init --recursive && \
	make -C vendor/libopencm3 && \
	make -C vendor/nanopb/generator/proto && \
	make -C firmware/protob && \
	make && \
	cp /tmp/trezor-mcu-bl/bootloader/bootloader.bin bootloader/bootloader.bin
	make -C firmware sign && \
	cp firmware/trezor.bin /$FIRMWARE_BINFILE && \
	cp firmware/trezor.elf /$FIRMWARE_ELFFILE
	"

/usr/bin/env python -c "
from __future__ import print_function
import hashlib
import sys
for arg in sys.argv[1:]:
  (fn, max_size) = arg.split(':')
  data = open(fn, 'rb').read()
  print('\n\n')
  print('Filename    :', fn)
  print('Fingerprint :', hashlib.sha256(hashlib.sha256(data).digest()).hexdigest())
  print('Size        : %d bytes (out of %d maximum)' % (len(data), int(max_size, 10)))
" $BOOTLOADER_BINFILE:32768 $FIRMWARE_BINFILE:491520
