# TREZOR Firmware

[![Build Status](https://travis-ci.org/trezor/trezor-mcu.svg?branch=master)](https://travis-ci.org/trezor/trezor-mcu) [![gitter](https://badges.gitter.im/trezor/community.svg)](https://gitter.im/trezor/community)

https://trezor.io/

## How to build TREZOR firmware?

1. <a href="https://docs.docker.com/engine/installation/">Install Docker</a>
2. `git clone https://github.com/trezor/trezor-mcu.git`
3. `cd trezor-mcu`
4. `./build-firmware.sh TAG` (where TAG is v1.5.0 for example, if left blank the script builds latest commit in master branch)

This creates file `build/trezor-TAG.bin` and prints its fingerprint and size at the end of the build log.

## How to build TREZOR bootloader?

1. <a href="https://docs.docker.com/engine/installation/">Install Docker</a>
2. `git clone https://github.com/trezor/trezor-mcu.git`
3. `cd trezor-mcu`
4. `./build-bootloader.sh TAG` (where TAG is bl1.3.2 for example, if left blank the script builds latest commit in master branch)

This creates file `build/bootloader-TAG.bin` and prints its fingerprint and size at the end of the build log.

## How to get fingerprint of firmware signed and distributed by SatoshiLabs?

1. Pick version of firmware binary listed on https://wallet.trezor.io/data/firmware/releases.json
2. Download it: `wget -O trezor.signed.bin https://wallet.trezor.io/data/firmware/trezor-1.3.6.bin`
3. Compute fingerprint: `tail -c +257 trezor.signed.bin | sha256sum`

Step 3 should produce the same sha256 fingerprint like your local build (for the same version tag). Firmware has a special header (of length 256 bytes) holding signatures themselves, which must be avoided while calculating the fingerprint, that's why tail command has to be used.
