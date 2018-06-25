#!/bin/bash
set -e

IMAGE=trezor-mcu-build

BOOTLOADER_TAG=${1:-master}
FIRMWARE_TAG=${2:-master}
REPOSITORY=${3:-trezor}

if [ "$REPOSITORY" = "local" ]; then
	REPOSITORY=file:///local/
else
	REPOSITORY=https://github.com/$REPOSITORY/trezor-mcu.git
fi

BOOTLOADER_BINFILE=build/bootloader-$BOOTLOADER_TAG.bin
BOOTLOADER_ELFFILE=build/bootloader-$BOOTLOADER_TAG.elf

FIRMWARE_BINFILE=build/trezor-$FIRMWARE_TAG.bin
FIRMWARE_ELFFILE=build/trezor-$FIRMWARE_TAG.elf

docker build -t $IMAGE .

echo
echo "STARTING BUILD:"
echo
echo "Building bootloader '$BOOTLOADER_TAG' + firmware '$FIRMWARE_TAG' from repo: $REPOSITORY"
echo

docker run -i -t -v $(pwd):/local -v $(pwd)/build:/build:z $IMAGE /bin/sh -c "\
	cd /tmp && \
	git clone $REPOSITORY trezor-mcu-bl && \
	cd trezor-mcu-bl && \
	git checkout $BOOTLOADER_TAG && \
	git submodule update --init --recursive && \
	make -C vendor/libopencm3 && \
	make && \
	make -C bootloader align && \
	cp bootloader/bootloader.bin /$BOOTLOADER_BINFILE && \
	cp bootloader/bootloader.elf /$BOOTLOADER_ELFFILE && \
	cd /tmp && \
	git clone $REPOSITORY trezor-mcu-fw && \
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

echo
echo "FINISHED BUILD"
echo

/usr/bin/env python -c "
from __future__ import print_function
import hashlib
import sys
for arg in sys.argv[1:]:
  (fn, fprint_start, hashing, max_size) = arg.split(':')
  fprint_start = int(fprint_start)
  max_size = int(max_size)
  data = open(fn, 'rb').read()
  if hashing == 'd':
      fprint = hashlib.sha256(hashlib.sha256(data[fprint_start:]).digest()).hexdigest()
  else:
      fprint = hashlib.sha256(data[fprint_start:]).hexdigest()
  print('Filename    :', fn)
  print('Fingerprint :', fprint)
  print('Size        : %d bytes (out of %d maximum)' % (len(data), max_size))
" $BOOTLOADER_BINFILE:0:d:32768 $FIRMWARE_BINFILE:256:s:491520
