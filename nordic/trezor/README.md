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

> Note: `build_sign_flash.sh` selects and pins the correct toolchain
> automatically. Launching the nRF shell manually is only needed if you want to
> run `west` or other NCS commands directly outside the script.

Launch the nRF shell with the toolchain matching the SDK you intend to build
for:

```sh
# For the default NCS 3.3.0 build
nrfutil toolchain-manager launch --shell --ncs-version v3.3.0

# For the regulatory-frozen NCS 2.9.0 build (t3w1_revA_nrf52832)
nrfutil toolchain-manager launch --shell --ncs-version v2.9.0
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

### Signing schemes (per SDK / model)

Which scheme a model uses follows its SDK, and the SDK is frozen per published
model for certification reasons — so both schemes are supported side by side and
`build_sign_flash.sh` picks one from the model it just built (never from a flag):

| Model | SDK | MCUboot revision | Scheme |
|-------|-----|------------------|--------|
| `t3w1` | NCS 2.9 | `trezor-v2.1.0-ncs3` | **legacy**: two Ed25519 signatures over the image hash (TLVs `0x00A0`/`0x00A1`), against the nRF's own key pool |
| `t3t2` | NCS 3.3 | `trezor-ncs3.3.0` | **founder**: post-quantum founder Merkle tree (`CONFIG_BOOT_PQ_SECURE_BOOT`) |

`CONFIG_BOOT_PQ_SECURE_BOOT` lives in a board-scoped fragment
(`sysbuild/mcuboot_t3t2.conf`) and must NOT reach t3w1: the symbol does not exist in
the NCS 2.9 MCUboot, and assigning an undefined symbol aborts the Kconfig run.

#### legacy (t3w1)

`imgtool` lays out the image and computes the image-hash TLV; `extract_hash.py` +
`hash_signer` + `insert_signatures.py` then add the two signatures. `-s` does all of
it, so the merged hex carries a bootable app.

#### founder (t3t2)

The image carries **no signature of its own**. Authenticity comes from the founder
Merkle tree: the image is a leaf under `modelRoot`, and the founder's hybrid
signature over `modelRoot` (SLH-DSA + Ed25519, 2-of-3) is the same one the Trezor STM
boot header carries. One post-quantum trust root covers both MCUs, and there is no
separate nRF signing step.

Which founder keys signed is declared by the image's PROTECTED sigmask TLV
(`0x00A2`) — protected, so it sits inside MCUboot's image hash *and* the founder
leaf, meaning the signature attests to the signer set. The build only emits a
**placeholder**; the signer stamps the real value (and re-stamps the image hash,
which protected TLVs are part of) before computing the leaf. That keeps founder key
rotation a re-sign rather than an nRF rebuild.

The founder signature only exists once the STM bootloader is signed, so signing is a
round trip through trezor-firmware. On a dev build (`-d`) the bare image is copied
there automatically:

```sh
# 1. build + lay out the bare image (copies it to core/embed/models/<MODEL>/)
./scripts/build_sign_flash.sh -b t3t2 -d -s

# 2. fold it into the founder tree and sign
(cd ../../core && make build_pq TREZOR_MODEL=T3T2 TREE_OPTS="--nrf-pq-native")

# 3. merge the signed image and flash ( -i with no path = take it from the bundle )
./scripts/build_sign_flash.sh -b t3t2 -d -s -f -i
```

Without `-i` the **bare** image is merged, which this MCUboot rejects — which is what
you want in order to install a new MCUboot, or to force an OTA push (the STM sees no
valid nRF app, so it cannot skip the update).

To check a signed image against a founder key pool without a flash cycle:
`core/tools/trezor_core_tools/nrf_pq_check.py <image>`.

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
