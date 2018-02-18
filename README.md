# TREZOR Firmware

[![Build Status](https://travis-ci.org/trezor/trezor-mcu.svg?branch=master)](https://travis-ci.org/trezor/trezor-mcu) [![gitter](https://badges.gitter.im/trezor/community.svg)](https://gitter.im/trezor/community)

https://trezor.io/

## How to build TREZOR firmware?

1. [Install Docker](https://docs.docker.com/engine/installation/)
2. `git clone https://github.com/trezor/trezor-mcu.git`
3. `cd trezor-mcu`
4. `./build-firmware.sh TAG` (where TAG is v1.5.0 for example, if left blank the script builds latest commit in master branch)

This creates file `build/trezor-TAG.bin` and prints its fingerprint and size at the end of the build log.

## How to build TREZOR emulator for Linux?

1. [Install Docker](https://docs.docker.com/engine/installation/)
2. `git clone https://github.com/trezor/trezor-mcu.git`
3. `cd trezor-mcu`
4. `./build-emulator.sh TAG` (where TAG is v1.5.0 for example, if left blank the script builds latest commit in master branch)

This creates binary file `build/trezor-emulator-TAG`, which can be run and works as a trezor emulator. (Use `TREZOR_OLED_SCALE` env. variable to make screen bigger.)

## How to build TREZOR bootloader?

1. [Install Docker](https://docs.docker.com/engine/installation/)
2. `git clone https://github.com/trezor/trezor-mcu.git`
3. `cd trezor-mcu`
4. `./build-bootloader.sh TAG` (where TAG is bl1.3.2 for example, if left blank the script builds latest commit in master branch)

This creates file `build/bootloader-TAG.bin` and prints its fingerprint and size at the end of the build log.

## How to get fingerprint of firmware signed and distributed by SatoshiLabs?

1. Pick version of firmware binary listed on https://wallet.trezor.io/data/firmware/releases.json
2. Download it: `wget -O trezor.signed.bin https://wallet.trezor.io/data/firmware/trezor-1.3.6.bin`
3. Compute fingerprint: `tail -c +257 trezor.signed.bin | sha256sum`

Step 3 should produce the same sha256 fingerprint like your local build (for the same version tag). Firmware has a special header (of length 256 bytes) holding signatures themselves, which must be avoided while calculating the fingerprint, that's why tail command has to be used.

## How to install custom built firmware?

**WARNING: This will erase the recovery seed stored on the device! You should never do this on TREZOR that contains coins!**

1. Install python-trezor: `pip install trezor` ([more info](https://github.com/trezor/python-trezor))
2. `trezorctl firmware_update -f build/trezor-TAG.bin`

## Building for development

If you want to build device firmware, make sure you have the
[GNU ARM Embedded toolchain](https://developer.arm.com/open-source/gnu-toolchain/gnu-rm/downloads) installed.

* If you want to build the emulator instead of the firmware, run `export EMULATOR=1 TREZOR_TRANSPORT_V1=1`
* If you want to build with the debug link, run `export DEBUG_LINK=1`. Use this if you want to run the device tests.
* When you change these variables, use `script/setup` to clean the repository

1. To initialize the repository, run `script/setup`
2. To build the firmware or emulator, run `script/cibuild`

If you are building device firmware, the firmware will be in `firmware/trezor.bin`.

You can launch the emulator using `firmware/trezor.elf`. To use `trezorctl` with the emulator, use
`trezorctl -t udp` (for example, `trezorctl -t udp get_features`).

If `trezorctl -t udp` appears to hang, make sure you have run `export TREZOR_TRANSPORT_V1=1`.
