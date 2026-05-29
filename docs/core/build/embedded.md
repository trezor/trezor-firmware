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

All Python dependencies and packages are handled with `uv`. If you work in nix-shell, `uv` will be installed automatically. Then, you can install the dependencies and run the `uv` shell in the repository root.

```sh
uv sync
source .venv/bin/activate
```

**Note: The recommended way of initializing your environment is to first run nix-shell and then initialize the `uv` shell within it.**

## Protobuf Compiler

The protocol buffer compiler `protoc` is needed to (unsurprisingly) compile protocol buffer files. [Follow the installation instructions for your system](https://grpc.io/docs/protoc-installation/).

## Rust

Install the appropriate target with [`rustup`](https://rustup.rs/):

```sh
rustup target add thumbv8m.main-none-eabihf # for T3xx
rustup target add thumbv7em-none-eabihf  # for T2xx
rustup target add thumbv7m-none-eabi     # for T1
```

## Building

Most `xtask` commands require specifying the model via the `--model` or `-m` option. You can select one of the following models:

- `t2t1` - Model T
- `t3b1` - Trezor Safe 3
- `t3t1` - Trezor Safe 5
- `t3w1` - Trezor Safe 7
- `d001` - STM32F429I-DISC1 Discovery Kit
- `d002` - STM32U5G9J-DK Discovery Kit


```sh
xtask build boardloader -m t3t1
xtask build bootloader -m t3t1
xtask build firmware -m t3t1
```

## Uploading

Use `xtask upload firmware --m t3t1` to upload the firmware to a production device.

* For TT: Do not forget to [enter bootloader](https://www.youtube.com/watch?v=3hes1H4qRbw) on the device beforehand.
* For TS3: You will have to [unlock bootloader](https://trezor.io/learn/a/unlocking-the-bootloader-on-trezor-safe-3) first. Make sure to read the link in completeness for potentially unwanted effects.

## Flashing

For flashing firmware to blank device (without bootloader) use `xtask flash firmware -m t3t1`.
You need to have OpenOCD installed.

## Building in debug mode

You can also build firmware in debug mode to see log output or run tests.

```sh
xtask build firmware -m t3t1 --pyopt=false
```

To get a full debug build, use:

```sh
xtask build firmware -m t3t1 --pyopt=false --btc-only --debug  !@#
```

Use `screen` to enter the device's console. Do not forget to add your user to the `dialout` group or use `sudo`. Note that both the group and the tty name can differ, use `ls -l /dev/tty*` or `ls /dev/tty* | grep usb` to find out proper names on your machine.

```sh
screen /dev/ttyACM0
```
