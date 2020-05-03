#!/usr/bin/env bash
set -e

IMAGE=trezor-firmware-build.nixos

TAG=${1:-master}
REPOSITORY=${2:-local}
PRODUCTION=${PRODUCTION:-1}
MEMORY_PROTECT=${MEMORY_PROTECT:-1}

if [ "$REPOSITORY" = "local" ]; then
  REPOSITORY=file:///local/
else
  REPOSITORY=https://github.com/$REPOSITORY/trezor-firmware.git
fi

docker build -t "$IMAGE" ci/

USER=$(ls -lnd . | awk '{ print $3 }')
GROUP=$(ls -lnd . | awk '{ print $4 }')

mkdir -p $(pwd)/build/core $(pwd)/build/legacy
mkdir -p $(pwd)/build/core-bitcoinonly $(pwd)/build/legacy-bitcoinonly

# build core

for BITCOIN_ONLY in 0 1; do

  DIRSUFFIX=${BITCOIN_ONLY/1/-bitcoinonly}
  DIRSUFFIX=${DIRSUFFIX/0/}

  docker run -it --rm \
    -v $(pwd):/local \
    -v $(pwd)/build/core"${DIRSUFFIX}":/build:z \
    --env BITCOIN_ONLY="$BITCOIN_ONLY" \
    --env PRODUCTION="$PRODUCTION" \
    --user="$USER:$GROUP" \
    "$IMAGE" \
    /nix/var/nix/profiles/default/bin/nix-shell --run "\
      cd /tmp && \
      git clone $REPOSITORY trezor-firmware && \
      cd trezor-firmware/core && \
      ln -s /build build &&
      git checkout $TAG && \
      git submodule update --init --recursive && \
      pipenv install && \
      pipenv run make clean vendor build_firmware"

done

# build legacy

for BITCOIN_ONLY in 0 1; do

  DIRSUFFIX=${BITCOIN_ONLY/1/-bitcoinonly}
  DIRSUFFIX=${DIRSUFFIX/0/}

  docker run -it --rm \
    -v $(pwd):/local \
    -v $(pwd)/build/legacy"${DIRSUFFIX}":/build:z \
    --env BITCOIN_ONLY="$BITCOIN_ONLY" \
    --env MEMORY_PROTECT="$MEMORY_PROTECT" \
    --user="$USER:$GROUP" \
    "$IMAGE" \
    /nix/var/nix/profiles/default/bin/nix-shell --run "\
      cd /tmp && \
      git clone $REPOSITORY trezor-firmware && \
      cd trezor-firmware/legacy && \
      ln -s /build build &&
      git checkout $TAG && \
      git submodule update --init --recursive && \
      pipenv install && \
      pipenv run script/cibuild && \
      mkdir -p build/firmware && \
      cp firmware/trezor.bin build/firmware/firmware.bin && \
      cp firmware/trezor.elf build/firmware/firmware.elf"

done
