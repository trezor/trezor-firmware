#!/usr/bin/env bash

# Cloning connect repository and running the tests from there

FILE_DIR="$(dirname "${0}")"
cd ${FILE_DIR}

CONNECT_DIR="connect"

# For quicker local usage, do not cloning connect repo if it already exists
if [[ ! -d "${CONNECT_DIR}" ]]
then
    git clone https://github.com/trezor/connect.git
    cd ${CONNECT_DIR}
    git submodule update --init --recursive
else
    cd ${CONNECT_DIR}
fi

# Taking an optional script argument with emulator version
if [ ! -z "${1}" ]
then
    EMU_VERSION="${1}"
else
    EMU_VERSION="2-master"
fi
echo "Will be running with ${EMU_VERSION} emulator"

# Using -d flag to disable docker, as tenv is already running on the background
nix-shell --run "yarn && tests/run.sh -d -f ${EMU_VERSION}"
