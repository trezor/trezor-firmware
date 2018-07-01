#!/bin/bash
set -e

IMAGE=trezor-core-build
TAG=${1:-master}
REPOSITORY=${2:-trezor}

if [ "$REPOSITORY" = "local" ]; then
	REPOSITORY=file:///local/
else
	REPOSITORY=https://github.com/$REPOSITORY/trezor-core.git
fi

docker build -t $IMAGE .

docker run -t -v $(pwd):/local -v $(pwd)/build-docker:/build:z $IMAGE /bin/sh -c "\
	git clone $REPOSITORY trezor-core && \
	cd trezor-core && \
	ln -s /build build &&
	git checkout $TAG && \
	git submodule update --init --recursive && \
	make clean vendor build_boardloader build_bootloader build_prodtest build_firmware"
