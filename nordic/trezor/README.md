# Trezor BLE Gateway

Welcome to the **Trezor BLE Gateway** project!
This repository contains the source code and instructions to build and flash the application onto the `t3w1_nrf52833` board.

## Table of Contents

- [Trezor BLE Gateway](#trezor-ble-gateway)
  - [Table of Contents](#table-of-contents)
  - [Prerequisites](#prerequisites)
  - [Getting Started](#getting-started)
    - [Install the toolchain](#install-the-toolchain)
    - [Launch the nRF Shell](#launch-the-nrf-shell)
    - [Initialize the Workspace](#initialize-the-workspace)
    - [Update nRF Connect SDK Modules](#update-nrf-connect-sdk-modules)
  - [Recommended build methods](#recommended-build-methods)
    - [Building and signing using script: debug, production](#building-and-signing-using-script-debug-production)
  - [Alternative build methods](#alternative-build-methods)
    - [Manually wrapping and signing the binary](#manually-wrapping-and-signing-the-binary)
    - [Building the Application](#building-the-application)
    - [Build Radio test application](#build-radio-test-application)
    - [Flashing the Application](#flashing-the-application)
    - [Build MCUBoot bootloader: debug, prod, default](#build-mcuboot-bootloader-debug-prod-default)
    - [Build Application](#build-application)

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
./scripts/build_sign_flash.sh -b t3w1_revA_nrf52832 -d
./scripts/build_sign_flash.sh -b t3w1_revA_nrf52832 -p
```

The output is signed with dev keys, appropriate for flashing on a board, or as an input
to the production signing process.

## Alternative build methods

### Manually wrapping and signing the binary
`nrftool wrap` needs to know the board name, from which it extracts the model identifier.
```sh
nrftool wrap build/trezor-ble/zephyr/zephyr.bin -o build/trezor-ble/zephyr/zephyr.wrapped.bin -b t3w1_revA_nrf52832
```
The result is a binary with a mcuboot header. Use `nrftool sign-dev` to sign it with dev keys.

`nrftool` transparently supports `.bin` and `.hex` files.

In order to produce a merged hex image for flashing, a separate script can be used:
```sh
python ../zephyr/scripts/build/mergehex.py build/mcuboot/zephyr/zephyr.hex build/trezor-ble/zephyr/zephyr.wrapped.hex -o build/trezor-ble/zephyr.merged.signed.hex
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
