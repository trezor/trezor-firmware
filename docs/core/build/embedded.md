# Build instructions for Embedded (ARM port)

First clone, initialize submodules and install Poetry as defined [here](index.md).
**Do not forget you need to be in a `poetry shell` environment!**

## Requirements

You will need the GCC ARM toolchain for building and OpenOCD for flashing to a device.
You will also need Python dependencies for signing.

### Debian/Ubuntu

```sh
sudo apt-get install scons gcc-arm-none-eabi libnewlib-arm-none-eabi llvm-dev libclang-dev clang
```

### NixOS

There is a `shell.nix` file in the root of the project. Just run the following
**before** entering the `core` directory:

```sh
nix-shell
```

### OS X

_Consider using [Nix](https://nixos.org/download.html). With Nix all you need to do is `nix-shell`._

For other users:

1. Download [gcc-arm-none-eabi](https://developer.arm.com/open-source/gnu-toolchain/gnu-rm/downloads)
2. Follow the [install instructions](https://launchpadlibrarian.net/287100883/readme.txt)
3. To install OpenOCD, run `brew install open-ocd`
4. Run `make vendor build_boardloader build_bootloader build_firmware`

## Rust

Install the appropriate target with [`rustup`](https://rustup.rs/):

```sh
rustup target add thumbv7em-none-eabihf  # for TT
rustup target add thumbv7m-none-eabi     # for T1
```

## Building

```sh
make vendor build_boardloader build_bootloader build_firmware
```

## Uploading

Use `make upload` to upload the firmware to a production device. Do not forget to [enter bootloader](https://wiki.trezor.io/User_manual:Updating_the_Trezor_device_firmware) on the device beforehand.

## Flashing

For flashing firmware to blank device (without bootloader) use `make flash`.
You need to have OpenOCD installed.

## Building in debug mode

You can also build firmware in debug mode to see log output or run tests.

```sh
PYOPT=0 make build_firmware
```

To get a full debug build, use:

```sh
make build_firmware BITCOIN_ONLY=0 PYOPT=0
```

You can then use `screen` to enter the device's console. Do not forget to add your user to the `dialout` group or use `sudo`. Note that both the group and the tty name can differ, use `ls -l` to find out proper names on your machine.

```sh
screen /dev/ttyACM0
```
