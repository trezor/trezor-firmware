# Trezor One Bootloader and Firmware

## Building with Docker

Ensure that you have Docker installed. You can follow [Docker's installation instructions](https://docs.docker.com/engine/installation/).

Clone this repository, then use `build-docker.sh` to build all images:
```sh
git clone https://github.com/trezor/trezor-firmware.git
cd trezor-firmware
./build-docker.sh
```

When the build is done, you will find the current firmware in `build/legacy/firmware/firmware.bin`.

### Running with sudo

It is possible to run `build-docker.sh` if either your Docker is configured in rootless mode,
or if your user is a member of the `docker` group; see [Docker documentation](https://docs.docker.com/install/linux/linux-postinstall/)
for details.

If you don't satisfy the above conditions, and run `sudo ./build-docker.sh`, you might receive a `Permission denied`
error. To work around it, make sure that the directory hierarchy in `build/` directory
is world-writable - e.g., by running `chmod -R a+w build/`.

## Building older versions

For firmware versions **1.8.1** and newer, you can checkout the respective tag locally.
To build firmware 1.8.2, for example, run `git checkout legacy/v1.8.2` and then use
the instructions below.

Note that the unified Docker build was added after version 1.8.3, so it is not available
for older versions.

For firmwares older than 1.8.1, please clone the archived [trezor-mcu](https://github.com/trezor/trezor-mcu) repository and follow the instructions in its README.

## Local development build

Make sure you have Python 3.6 or later and [Poetry](https://python-poetry.org/)
installed.

If you want to build device firmware, also make sure that you have the [GNU ARM Embedded toolchain](https://developer.arm.com/open-source/gnu-toolchain/gnu-rm/downloads) installed.
See [Dockerfile](../../ci/Dockerfile#L72-L76) for up-to-date version of the toolchain.

The build process is configured via environment variables:

* `EMULATOR=1` specifies that an emulator should be built, instead of the device firmware.
* `DEBUG_LINK=1` specifies that DebugLink should be available in the built image.
* `MEMORY_PROTECT=0` disables memory protection. This is necessary for installing unofficial firmware.
* `DEBUG_LOG=1` enables debug messages to be printed on device screen.
* `BITCOIN_ONLY=1` specifies Bitcoin-only version of the firmware.

To run the build process, execute the following commands:

```sh
# enter the legacy subdirectory
cd legacy
# set up poetry
poetry install
# set up environment variables. For example, to build emulator with debuglink:
export EMULATOR=1 DEBUG_LINK=1
# clear build artifacts
poetry run ./script/setup
# run build process
poetry run ./script/cibuild
```

A built device firmware will be located in `legacy/firmware/trezor.bin`. A built emulator will be
located in `legacy/firmware/trezor.elf`.

### Common errors

* **"Exception: bootloader has to be smaller than 32736 bytes"**: if you didn't modify the bootloader
  source code, simply make sure you always run `./script/setup` before runnning `./script/cibuild`

* **"error adding symbols: File in wrong format"**: This happens when building emulator after building
  the firmware, or vice-versa. Execute the following command to fix the problem:
  ```sh
  find -L vendor -name "*.o" -delete
  ```

You can launch the emulator using `./firmware/trezor.elf`. To use `trezorctl` with the emulator, use
`trezorctl -p udp` (for example, `trezorctl -p udp get_features`).

You can use `TREZOR_OLED_SCALE` environment variable to make emulator screen bigger.

## How to get fingerprint of firmware signed and distributed by SatoshiLabs?

1. Pick version of firmware binary listed on https://data.trezor.io/firmware/1/releases.json
2. Download it: `wget -O trezor.signed.bin https://data.trezor.io/firmware/1/trezor-1.9.4.bin`
3. Use `trezorctl` dry-run mode to get the firmware fingerprint:
   ```sh
   trezorctl firmware-update -n -f trezor.signed.bin
   ```

Step 3 should produce the same fingerprint like your local build (for the same version tag).

## How to install custom built firmware?

**WARNING: This will erase the recovery seed stored on the device! You should never do this on Trezor that contains coins!**

Build with `MEMORY_PROTECT=0` or you will get a hard fault on your device.

Switch your device to bootloader mode, then execute:
```sh
trezorctl firmware-update -f build/legacy/firmware/firmware.bin
```

## Combining bootloader and firmware with various `MEMORY_PROTECT` settings, signed/unsigned

Not all combinations of bootloader and firmware will work. This depends on
3 variables: MEMORY_PROTECT of bootloader, MEMORY_PROTECT of firmware, whether firmware is signed

This table shows the result for bootloader 1.8.0+ and 1.9.1+:

| Bootloader MEMORY_PROTECT | Firmware MEMORY_PROTECT | Is firmware officially signed? | Result                                                                                     |
| ------------------------- | ----------------------- | ------------------------------ | ------------------------------------------------------------------------------------------ |
|  1                        |  1                      | yes                            | works, official configuration                                                              |
|  1                        |  1                      | no                             | hardfault in header.S when setting VTOR and stack                                          |
|  0                        |  1                      | no                             | works, but don't forget to comment out `check_and_replace_bootloader`, otherwise it'll get overwritten |
|  0                        |  0                      | no                             | hard fault because header.S doesn't set VTOR and stack right                               |
|  1                        |  0                      | no                             | works                                                                                      |

The other three possibilities with signed firmware and `MEMORY_PROTECT!=0` for bootloader/firmware don't exist.

