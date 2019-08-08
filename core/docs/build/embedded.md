# Build instructions for Embedded (ARM port)

First clone, initialize submodules and install Pipenv as defined [here](index.md).

## Requirements

You will need the GCC ARM toolchain for building and OpenOCD for flashing to a device.
You will also need Python dependencies for signing.

### Debian/Ubuntu

```sh
sudo apt-get install scons gcc-arm-none-eabi libnewlib-arm-none-eabi
```

### OS X

1. Download [gcc-arm-none-eabi](https://developer.arm.com/open-source/gnu-toolchain/gnu-rm/downloads)
2. Follow the [install instructions](https://launchpadlibrarian.net/287100883/readme.txt)
3. To install OpenOCD, run `brew install open-ocd`
4. Run `pipenv run make vendor build_boardloader build_bootloader build_firmware`

## Building

```sh
pipenv run make vendor build_boardloader build_bootloader build_firmware
```

## Uploading

Use `make upload` to upload the firmware to a production device. Do not forget to [enter bootloader](https://wiki.trezor.io/User_manual-Updating_the_Trezor_device_firmware__TT) on the device beforehand.

## Flashing

For flashing firmware to blank device (without bootloader) use `make flash`,
or `make flash STLINK_VER=v2-1` if using a ST-LINK/V2.1 interface.
You need to have OpenOCD installed.

## Building in debug mode

You can also build firmware in debug mode to see log output or run tests. To avoid building firmware in debug mode accidentally, we do not provide a _make_ target. You need to rewrite `PYOPT` variable to `0` in `SConscript.firmware` file and then build the same way. The change is intentionally not _gitignored_.

```sh
sed -i "s/^PYOPT = '1'$/PYOPT = '0'/" SConscript.firmware
pipenv run make build_firmware
```

You can then use `screen` to enter the device's console. Do not forget to add your user to the `dialout` group or use `sudo`. Note that both the group and the tty name can differ, use `ls -l` to find out proper names on your machine.

```sh
screen /dev/ttyACM0
```
