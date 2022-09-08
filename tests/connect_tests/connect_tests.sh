#!/usr/bin/env bash

# Cloning trezor-suite repository and running connect tests from there

FILE_DIR="$(dirname "${0}")"
cd ${FILE_DIR}

TREZOR_SUITE_DIR="trezor-suite"

# For quicker local usage, do not cloning connect repo if it already exists
if [[ ! -d "${TREZOR_SUITE_DIR}" ]]
then
    git clone https://github.com/trezor/trezor-suite.git
    cd ${TREZOR_SUITE_DIR}
    git submodule update --init --recursive
else
    cd ${TREZOR_SUITE_DIR}
fi

echo "Changing 'localhost' to '127.0.0.1' in websocket client as a workaround for CI servers"
sed -i 's/localhost/127.0.0.1/g' ./packages/integration-tests/websocket-client.js

# Taking an optional script argument with emulator version
if [ ! -z "${1}" ]
then
    EMU_VERSION="${1}"
else
    EMU_VERSION="2-master"
fi
echo "Will be running with ${EMU_VERSION} emulator"

# Using -d flag to disable docker, as tenv is already running on the background
nix-shell --run "yarn && yarn build:libs && ./docker/docker-connect-test.sh node -p methods -d -c -f ${EMU_VERSION} -e checkFirmwareAuthenticity"
