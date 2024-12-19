# Build instructions for Embedded (ARM port)


First, clone the repository and initialize the submodules as defined [here](index.md).

Then, you need to install all necessary requirements.

## Requirements

The recommended way to control the requirements across all systems is to install **nix-shell**, which automatically installs all requirements in an isolated environment using the `shell.nix` configuration file located in the repository root.

To install nix-shell, follow the instructions [here](https://nix.dev/manual/nix/2.18/installation/installing-binary).

Once nix-shell is installed, go to the **repository root** and run:

```sh
nix-shell
```

### Working with Developer Tools

If you need to work with embedded development tools such as OpenOCD, gcc-arm-embedded, gdb, etc., you can run nix-shell with the following argument to enable additional development tools:

```sh
nix-shell --arg devTools true
```

### Manual Requirements Installation

If you prefer to install the requirements manually, look into the shell.nix file where you can find a list of requirements with versions.

## Python Dependencies

All Python dependencies and packages are handled with Poetry. If you work in nix-shell, Poetry will be installed automatically. Then, you can install the dependencies and run the Poetry shell in the repository root.

```sh
poetry install
poetry shell
```

**Note: The recommended way of initializing your environment is to first run nix-shell and then initialize the Poetry shell within it.**

## Protobuf Compiler

The protocol buffer compiler `protoc` is needed to (unsurprisingly) compile protocol buffer files. [Follow the installation instructions for your system](https://grpc.io/docs/protoc-installation/).

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

Use `make upload` to upload the firmware to a production device.

* For TT: Do not forget to [enter bootloader](https://www.youtube.com/watch?v=3hes1H4qRbw) on the device beforehand.
* For TS3: You will have to [unlock bootloader](https://trezor.io/learn/a/unlocking-the-bootloader-on-trezor-safe-3) first. Make sure to read the link in completeness for potentially unwanted effects.

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

Use `screen` to enter the device's console. Do not forget to add your user to the `dialout` group or use `sudo`. Note that both the group and the tty name can differ, use `ls -l /dev/tty*` or `ls /dev/tty* | grep usb` to find out proper names on your machine.

```sh
screen /dev/ttyACM0
```
