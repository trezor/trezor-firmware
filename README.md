# TREZOR Firmware

[![Build Status](https://travis-ci.org/trezor/trezor-mcu.svg?branch=master)](https://travis-ci.org/trezor/trezor-mcu) [![gitter](https://badges.gitter.im/trezor/community.svg)](https://gitter.im/trezor/community)

http://bitcointrezor.com/

## How to build TREZOR firmware?

1. <a href="https://docs.docker.com/engine/installation/">Install Docker</a>
2. `git clone https://github.com/trezor/trezor-mcu.git`
3. `cd trezor-mcu`
4. `./firmware-docker-build.sh TAG` (where TAG is v1.3.2 for example, if left blank the script builds latest commit)

This creates file `output/trezor-TAG.bin` and prints its fingerprint at the last line of the build log.

## How to build TREZOR bootloader?

1. <a href="https://docs.docker.com/engine/installation/">Install Docker</a>
2. `git clone https://github.com/trezor/trezor-mcu.git`
3. `cd trezor-mcu`
4. `./bootloader-docker-build.sh`

This creates file `output/bootloader.bin` and prints its fingerprint and size at the last line of the build log.

## How to get fingerprint of firmware signed and distributed by SatoshiLabs?

1. Pick version of firmware binary listed on https://wallet.mytrezor.com/data/firmware/releases.json
2. Download it: `wget -O trezor.signed.bin https://wallet.mytrezor.com/data/firmware/trezor-1.3.6.bin`
3. `./firmware-fingerprint.sh trezor.signed.bin`

Step 3 should produce the same sha256 fingerprint like your local build (for the same version tag).

The reasoning for `firmware-fingerprint.sh` script is that signed firmware has special header holding signatures themselves, which must be avoided while calculating the fingerprint.
