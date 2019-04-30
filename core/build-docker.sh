#!/bin/sh
set -e

cd "$(dirname $0)/.."

if [ "$1" = "--gcc_source" ]; then
	TOOLCHAIN_FLAVOR=src
	shift
else
	TOOLCHAIN_FLAVOR=linux
fi

IMAGE=trezor-core-build.$TOOLCHAIN_FLAVOR
TAG=${1:-master}
REPOSITORY=${2:-trezor}
PRODUCTION=${PRODUCTION:-0}

if [ "$REPOSITORY" = "local" ]; then
	REPOSITORY=file:///local/
else
	REPOSITORY=https://github.com/$REPOSITORY/trezor-firmware.git
fi

docker build -t $IMAGE --build-arg TOOLCHAIN_FLAVOR=$TOOLCHAIN_FLAVOR .

USER=$(ls -lnd . | awk '{ print $3 }')
GROUP=$(ls -lnd . | awk '{ print $4 }')

mkdir -p $(pwd)/build/core
docker run -t -v $(pwd):/local -v $(pwd)/build/core:/build:z --user="$USER:$GROUP" $IMAGE /bin/sh -c "\
	cd /tmp && \
	git clone $REPOSITORY trezor-firmware && \
	cd trezor-firmware/core && \
	ln -s /build build &&
	git checkout $TAG && \
	git submodule update --init --recursive && \
	PRODUCTION=$PRODUCTION make clean vendor build_boardloader build_bootloader build_firmware"
