#!/bin/bash

SITE="http://firmware.corp.sldev.cz/emulators/"
VERSIONS=(
    "legacy-v1.6.2"
    "legacy-v1.6.3"
    "legacy-v1.7.0"
    "legacy-v1.7.1"
    "legacy-v1.7.2"
    "legacy-v1.7.3"
    "legacy-v1.8.0"
    "legacy-v1.8.1"
    "core-v2.1.0"
)

for i in "${VERSIONS[@]}"; do
    # TODO: replace with CI variables
    # -nc: skip if present
    wget -nc --user X --password X "${SITE}trezor-emu-$i" -P emulators/
    chmod u+x "emulators/trezor-emu-$i"  # TODO is this a good idea?
done
