# Reproducible build

We want to invite the wider community to participate in the verification of the firmware
built by Trezor Company. With reasonable effort you should be able to build the firmware
and verify that it's identical to the official firmware.

Trezor Firmware uses [Nix](https://nixos.org/), [Poetry](https://python-poetry.org/) and
[Cargo](https://doc.rust-lang.org/cargo/) to make the build environment deterministic.
We also provide a Docker-based script so that the build can be performed with a single
command on usual x86 Linux system.

## Building

First you need to determine which *version tag* you want to build:
* for Trezor One it is `legacy/vX.Y.Z`, e.g. `legacy/v1.10.3`,
* for newer models, it is `core/vX.Y.Z`, e.g. `core/v2.4.2`.

Assuming you want to build `core/v2.8.3`:

1. install [Docker](https://www.docker.com/)
2. clone the firmware repository: `git clone https://github.com/trezor/trezor-firmware.git`
3. go into the firmware directory: `cd trezor-firmware`
4. checkout the version tag: `git checkout core/v2.8.3`
5. run: `bash build-docker.sh core/v2.8.3`

After the build finishes the firmware images are located in:
* `build/legacy/firmware/firmware.bin` and `build/legacy-bitcoinonly/firmware/firmware.bin` for Trezor One,
* `build/core-<model>/firmware/firmware.bin` and `build/core-<model>-bitcoinonly/firmware/firmware.bin` for later models.

### Model identifiers

You can speed up the build process by adding options to the script:

* `--models=A,B,C` to only build for specific model(s) which are not Trezor One.

The following models are supported:

* **`T1B1`** - Trezor One
* **`T2T1`** - Trezor Model T
* **`T2B1`** - Trezor Safe 3 rev.A
* **`T3B1`** - Trezor Safe 3 rev.B
* **`T3T1`** - Trezor Safe 5

Examples:

```sh
bash build-docker.sh --models=T1B1 legacy/v1.10.3  # build only for Trezor One
bash build-docker.sh --models=T3T1 core/v2.8.3  # build only for Trezor Safe 5
```

## Verifying

The result won't be bit-by-bit identical with the official images because the
official images are signed while local builds aren't.

### Trezor T and the Safe family

You can use `trezorctl` to download the official firmware image for your device:

```sh
trezorctl firmware download --model t3t1 --version 2.8.3
```

Or locate the firmware image in the [Trezor Data repository](https://github.com/trezor/data/tree/master/firmware).

The firmware binary starts with a [vendor header](../hardware/model-t/boot.md#vendor-header)
whose size is:

* Model T: 4608 bytes
* Safe 3: 512 bytes
* Safe 5: 1024 bytes

The vendor header is followed by a [firmware header](../hardware/model-t/boot.md#firmware-header)
that contains a 65-byte signature at offset `0x3bf` (959 in decimal).

You will need to calculate the right offset for the signature based on the model:

* Model T: 4608 + 959 = 5567
* Safe 3: 512 + 959 = 1471
* Safe 5: 1024 + 959 = 1983

Zero out the signature data to obtain an image identical to the one built locally:

```sh
OFFSET=<your offset here>
# the following line removes 65 bytes of signature data from the official firmware
dd if=/dev/zero of=trezor-t3t1-2.8.3.bin bs=1 seek=$OFFSET count=65 conv=notrunc

# the following two lines print out the hashes of the firmwares
sha256sum trezor-t3t1-2.8.3.bin
sha256sum build/core-T3T1/firmware/firmware.bin
```

### Trezor One

You can use `trezorctl` to download the official firmware image for your device:

```sh
trezorctl firmware download --model 1 --version 1.10.3
```

Or locate the firmware image in the [Trezor Data repository](https://github.com/trezor/data/tree/master/firmware).

Official Trezor One firmware older than 1.12 starts with [256-byte legacy
header](../hardware/model-one/firmware-format.md) used for compatibility with old
bootloaders. Locally built firmware doesn't have this header.

```
# strip legacy header
tail -c +257 trezor-1.10.3.bin > trezor-1.10.3-nolegacyhdr.bin
```

The [v2 header](../hardware/model-one/firmware-format.md#v2-header) has 3x65
bytes of signature data at offset 0x220. Overwrite by zeros to obtain image
identical to the one built locally.

```
dd if=/dev/zero of=trezor-1.10.3-nolegacyhdr.bin bs=1 seek=544 count=195 conv=notrunc

sha256sum trezor-1.10.3-nolegacyhdr.bin
sha256sum build/legacy/firmware/firmware.bin
```

_Note: Fingerprints displayed for T1 at the end of `build-docker.sh` do not match fingerprints of
official firmware due to the legacy header._

_Note: T1 firmware built this way won't boot because unsigned firmware needs to be built with
[`PRODUCTION=0`](../legacy/index.md#combining-bootloader-and-firmware-with-various-production-settings-signedunsigned)._
