# Trezor BLE Gateway

Welcome to the **Trezor BLE Gateway** project!
This repository contains the source code and instructions to build and flash the application onto the `t3w1_nrf52833` board.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
    - [Install the toolchain](#install-the-toolchain)
    - [Launch the nRF Shell](#launch-the-nrf-shell)
    - [Initialize the Workspace](#initialize-the-workspace)
    - [Update nRF Connect SDK Modules](#update-nrf-connect-sdk-modules)
    - [Build the Application](#build-the-application)
    - [Flash the Application](#flash-the-application)
- [Contributing](#contributing)
- [License](#license)

## Prerequisites

Before you begin, ensure you have met the following requirements:

- **nrfutil**: Install [nrfutil](https://docs.nordicsemi.com/bundle/nrfutil/page/README.html). This tool is essential for managing the nRF Connect SDK and toolchains.
- **Git**: Ensure you have Git installed for cloning repositories.

## Getting Started

Follow these steps to set up the project on your local machine.

### Install the toolchain

Using nrfutil, install the required toolchain for the nRF Connect SDK:
```sh
nrfutil toolchain-manager install --ncs-version v2.9.0
```

### Launch the nRF Shell

First, launch the nRF shell using the `nrfutil` toolchain manager and set the NCS to chosen version:

```sh
nrfutil toolchain-manager launch --shell
```

### Initialize the Workspace
Initialize your West workspace for the Trezor BLE Gateway project:
```sh
cd nordic
west init -l ./trezor
```

### Update nRF Connect SDK Modules

Update the modules:
```sh
west update
```


## Recommended build methods


### Building and signing using script: debug, production
To be invoked from nix-shell in nordic/trezor folder.
```sh
./scripts/build_sign_flash.sh -b t3w1_revA_nrf52832 -d -s
./scripts/build_sign_flash.sh -b t3w1_revA_nrf52832 -p -s
```

## Alternative build methods

### Signing custom method
hash_signer needs to be invoked from nix-shell.
```sh
imgtool sign --version 0.1.0+0 --align 4 --header-size 0x200 -S 0x6c000 --pad-header build/trezor-ble/zephyr/zephyr.bin build/trezor-ble/zephyr/zephyr.prep.bin --custom-tlv 0x00A2 0x3
imgtool sign --version 0.1.0+0 --align 4 --header-size 0x200 -S 0x6c000 --pad-header build/trezor-ble/zephyr/zephyr.hex build/trezor-ble/zephyr/zephyr.prep.hex --custom-tlv 0x00A2 0x3
imgtool dumpinfo  ./build/trezor-ble/zephyr/zephyr.prep.bin >> ./build/trezor-ble/zephyr/dump.txt
python ./scripts/extract_hash.py ./build/trezor-ble/zephyr/dump.txt
hash_signer -d e3d47ab7e90f15badb1a2fac8c082b727c3fa24f1238ad8607b67f720a63c4e9
python ./scripts/insert_signatures.py ./build/trezor-ble/zephyr/zephyr.prep.hex 0x82a2258db3da5c14ceddfff92e39531c873f870bad81a66506d706fd31da4ab4ad8e76d62686f0b0bbcf02dd4473d27b3bf0a2b98182d8b52bb2f1336eb7630d 0x0003 -o ./build/trezor-ble/zephyr/zephyr.signed_trz.hex
python ./scripts/insert_signatures.py ./build/trezor-ble/zephyr/zephyr.prep.bin 0x82a2258db3da5c14ceddfff92e39531c873f870bad81a66506d706fd31da4ab4ad8e76d62686f0b0bbcf02dd4473d27b3bf0a2b98182d8b52bb2f1336eb7630d 0x0003 -o ./build/trezor-ble/zephyr/zephyr.signed_trz.bin
python ../zephyr/scripts/build/mergehex.py  build/mcuboot/zephyr/zephyr.hex build/trezor-ble/zephyr/zephyr.signed_trz.hex -o build/trezor-ble/zephyr.merged.signed.hex
west flash --hex-file ./build/trezor-ble/zephyr.merged.signed.hex
```


### Building the Application
```sh
cd trezor
west build ./trezor-ble -b t3w1_revA_nrf52832 --sysbuild
```

When building for first time, add `--pristine=always` so that NCS versions and their cached files don't mix and fubar each other.

Debug builds can be built using the debug overlay configuration:
Build the application for the t3w1_revA_nrf52832 board:

```sh
west build ./trezor-ble -b t3w1_revA_nrf52832 --sysbuild -- -DOVERLAY_CONFIG=debug.conf
```


### Build Radio test application
```sh
cd trezor
west build ./radio_test/ -b t3w1_revA_nrf52832 --sysbuild --pristine
```

### Flashing the Application
Flash the compiled application onto the board:
```sh
west flash
```


### Build MCUBoot bootloader: debug, prod, default
```sh
west build ./trezor-ble -b t3w1_revA_nrf52832 --sysbuild --domain mcuboot -- -Dmcuboot_EXTRA_CONF_FILE="$PWD/trezor-ble/sysbuild/mcuboot.conf;$PWD/trezor-ble/sysbuild/mcuboot_debug.conf"
west build ./trezor-ble -b t3w1_revA_nrf52832 --sysbuild --domain mcuboot -- -Dmcuboot_EXTRA_CONF_FILE="$PWD/trezor-ble/sysbuild/mcuboot.conf;$PWD/trezor-ble/sysbuild/prod.conf"
west build ./trezor-ble -b t3w1_revA_nrf52832 --sysbuild --domain mcuboot
```

### Build Application
```sh
west build ./trezor-ble -b t3w1_revA_nrf52832 --sysbuild --domain trezor-ble -- -DOVERLAY_CONFIG=debug.conf
```
