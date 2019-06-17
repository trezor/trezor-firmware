# Trezor One Bootloader and Firmware

[![Build Status](https://travis-ci.org/trezor/trezor-mcu.svg?branch=master)](https://travis-ci.org/trezor/trezor-mcu) [![gitter](https://badges.gitter.im/trezor/community.svg)](https://gitter.im/trezor/community)

https://trezor.io/

## How to build the Trezor bootloader, firmware and emulator

Ensure that you have Docker installed. You can follow [Docker's installation instructions](https://docs.docker.com/engine/installation/).

Clone this repository:
```sh
git clone https://github.com/trezor/trezor-mcu.git`
cd trezor-mcu
```

Use the `build.sh` command to build the images.

* to build bootloader 1.6.0 and firmware 1.7.0:
  ```sh
  ./build.sh bl1.6.0 v1.7.0
  ```
* to build latest firmware from master:
  ```sh
  ./build.sh
  ```
* to build the emulator from master:
  ```sh
  ./build.sh EMU
  ```
* to build the emulator for version 1.7.0:
  ```sh
  ./build.sh EMU v1.7.0
  ```

Build results are stored in the `build/` directory. File `bootloader-<tag>.bin` represents
the bootloader, `trezor-<tag>.bin` is the firmware image, and `trezor-emulator-<tag>.elf`
is the emulator executable.

You can use `TREZOR_OLED_SCALE` environment variable to make emulator screen bigger.

## How to get fingerprint of firmware signed and distributed by SatoshiLabs?

1. Pick version of firmware binary listed on https://wallet.trezor.io/data/firmware/1/releases.json
2. Download it: `wget -O trezor.signed.bin https://wallet.trezor.io/data/firmware/1/trezor-1.6.1.bin`
3. Compute fingerprint: `tail -c +257 trezor.signed.bin | sha256sum`

Step 3 should produce the same sha256 fingerprint like your local build (for the same version tag). Firmware has a special header (of length 256 bytes) holding signatures themselves, which must be avoided while calculating the fingerprint, that's why tail command has to be used.

## How to install custom built firmware?

**WARNING: This will erase the recovery seed stored on the device! You should never do this on Trezor that contains coins!**

1. Install python-trezor: `pip install trezor` ([more info](https://github.com/trezor/python-trezor))
2. `trezorctl firmware_update -f build/trezor-TAG.bin`

## Building for development

If you want to build device firmware, make sure you have the
[GNU ARM Embedded toolchain](https://developer.arm.com/open-source/gnu-toolchain/gnu-rm/downloads) installed.
You will also need Python 3.5 or later and [pipenv](https://pipenv.readthedocs.io/en/latest/install/).

* If you want to build the emulator instead of the firmware, run `export EMULATOR=1 TREZOR_TRANSPORT_V1=1`
* If you want to build with the debug link, run `export DEBUG_LINK=1`. Use this if you want to run the device tests.
* When you change these variables, use `script/setup` to clean the repository

1. To initialize the repository, run `script/setup`
2. To initialize a Python environment, run `pipenv install`
3. To build the firmware or emulator, run `pipenv run script/cibuild`

If you are building device firmware, the firmware will be in `firmware/trezor.bin`.

You can launch the emulator using `firmware/trezor.elf`. To use `trezorctl` with the emulator, use
`trezorctl -p udp` (for example, `trezorctl -p udp get_features`).
