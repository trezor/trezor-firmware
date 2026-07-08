# Trezor BLE Gateway

Welcome to the **Trezor BLE Gateway** project!
This repository contains the source code and instructions to build and flash the
application. Two boards are supported, each tied to a specific nRF Connect SDK:
the `t3w1_revA_nrf52832` board on the regulatory-frozen **NCS v2.9.0**, and the
`t3t2_dk` (nRF54LS05B) board on the default **NCS v3.3.0** — see
[Selecting the nRF Connect SDK version](#selecting-the-nrf-connect-sdk-version).

## Table of Contents

- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
    - [Install the toolchain](#install-the-toolchain)
    - [Launch the nRF Shell](#launch-the-nrf-shell)
    - [Initialize the Workspace](#initialize-the-workspace)
    - [Update nRF Connect SDK Modules](#update-nrf-connect-sdk-modules)
    - [Selecting the nRF Connect SDK version](#selecting-the-nrf-connect-sdk-version)
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

Using nrfutil, install the toolchain for the nRF Connect SDK. The project
defaults to **NCS v3.3.0**; install the matching toolchain:
```sh
nrfutil toolchain-manager install --ncs-version v3.3.0
```

The regulatory-frozen build still uses **NCS v2.9.0**. If you need to switch to
it (see [Selecting the SDK version](#selecting-the-nrf-connect-sdk-version)),
install that toolchain as well:
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

### Selecting the nRF Connect SDK version

The workspace ships two manifests, sharing a single checkout:

| Manifest            | SDK        | Role                              |
|---------------------|------------|-----------------------------------|
| `west.yml`          | NCS v3.3.0 | **Default** (used by `west init`) |
| `west-ncs2.9.yml`   | NCS v2.9.0 | Regulatory-frozen, occasional     |

`west init -l ./trezor` selects `west.yml` (3.3.0). To switch the active
manifest, change it and re-run `west update` in the same workspace:

```sh
# Drop to the frozen 2.9.x SDK
west config manifest.file west-ncs2.9.yml
west update

# Return to the default 3.3.x SDK
west config manifest.file west.yml
west update
```

Each board is tied to one SDK — build the matching board for the active manifest:

| Manifest          | SDK        | Board to build                |
|-------------------|------------|-------------------------------|
| `west.yml`        | NCS v3.3.0 | `t3t2_dk/nrf54ls05b/cpuapp` |
| `west-ncs2.9.yml` | NCS v2.9.0 | `t3w1_revA_nrf52832`          |

The nRF54L (t3t2_dk) is not supported on NCS 2.9, so it can only be built under
the default manifest.

Notes:
- Only one SDK is checked out at a time, so always rebuild with
  `--pristine=always` after switching.
- Switch the toolchain to match the manifest (`nrfutil toolchain-manager
  launch --shell` with the corresponding NCS version), or builds will fail in
  confusing ways.
- SDK differences in application **code** are handled with `<ncs_version.h>`,
  writing for the current default (3.3) and gating the older SDK as the
  exception: `#if NCS_VERSION_NUMBER < 0x030300  /* NCS 2.9 */ … #else … #endif`.
- Board/SoC differences in **Kconfig and devicetree** go in
  `boards/<board>.{conf,overlay}` (auto-merged by Zephyr for the matching board).
  Since each board targets a single SDK, this also covers version-specific
  config/DT without a separate version gate.


## Recommended build methods


### Building and signing using script: debug, production
To be invoked from nix-shell in nordic/trezor folder.

`-b` accepts either a full board target (e.g. `t3t2_dk/nrf54ls05b/cpuapp`) or a
short model alias that expands to that model's default board: `t3t2` →
`t3t2_dk/nrf54ls05b/cpuapp`, `t3w1` → `t3w1_revA_nrf52832`.
```sh
./scripts/build_sign_flash.sh -b t3w1 -d -s
./scripts/build_sign_flash.sh -b t3w1 -p -s
```

For the `t3t2_dk` (nRF54LS05B) board, first make sure the default NCS v3.3.0
manifest and toolchain are active (see
[Selecting the nRF Connect SDK version](#selecting-the-nrf-connect-sdk-version)):
```sh
./scripts/build_sign_flash.sh -b t3t2 -d -s
./scripts/build_sign_flash.sh -b t3t2 -p -s
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

To build for the `t3t2_dk` (nRF54LS05B) board, switch to the default NCS v3.3.0
manifest first (see [Selecting the nRF Connect SDK version](#selecting-the-nrf-connect-sdk-version)):

```sh
west build ./trezor-ble -b t3t2_dk/nrf54ls05b/cpuapp --sysbuild -- -DOVERLAY_CONFIG=debug.conf
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
