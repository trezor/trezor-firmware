# Reproducible build

We want to invite the wider community to participate in the verification of
the firmware built by SatoshiLabs. With reasonable effort you should be able to
build the firmware and verify that it's identical to the official firmware.

Trezor Firmware uses [Nix](https://nixos.org/), [Poetry](https://python-poetry.org/)
and [Cargo](https://doc.rust-lang.org/cargo/) to make the build environment
deterministic. We also provide a Docker-based script so that the build can be
performed with a single command on usual x86 Linux system.

## Building

First you need to determine which *version tag* you want to build:
* for Trezor One it is `legacy/vX.Y.Z`, e.g. `legacy/v1.10.3`,
* for Trezor Model T it is `core/vX.Y.Z`, e.g. `core/v2.4.2`.

Assuming you want to build `core/v2.4.2`:

1. install [Docker](https://www.docker.com/)
2. clone the firmware repository: `git clone https://github.com/trezor/trezor-firmware.git`
3. go into the firmware directory: `cd trezor-firmware`
4. checkout the version tag: `git checkout core/v2.4.2`
5. run: `bash build-docker.sh core/v2.4.2`

After the build finishes the firmware images are located in:
* `build/legacy/firmware/firmware.bin` and `build/legacy-bitcoinonly/firmware/firmware.bin` for Trezor One,
* `build/core/firmware/firmware.bin` and `build/core-bitcoinonly/firmware/firmware.bin` for Trezor Model T.

## Verifying

The result won't be bit-by-bit identical with the official images because the
official images are signed while local builds aren't. Official release of
Trezor One firmware also has additional 256-byte legacy header that needs to be
removed first.

### Trezor T

The [firmware header](../hardware/model-t/boot.md#firmware-header) contains 65
bytes of signature data at offset 0x15bf. After overwriting it by zeros in
official release the binaries should become identical.

```
wget https://data.trezor.io/firmware/2/trezor-2.4.2.bin

# the following line removes 65 bytes of signature data from the official firmware
dd if=/dev/zero of=trezor-2.4.2.bin bs=1 seek=5567 count=65 conv=notrunc

# the following two lines print out the hashes of the firmwares
sha256sum trezor-2.4.2.bin
sha256sum build/core/firmware/firmware.bin
```

### Trezor One

Official T1 firmware starts with [256-byte legacy header](../hardware/model-one/firmware-format.md)
used for compatibility with old bootloaders. Locally built firmware doesn't have this header.

```
wget https://data.trezor.io/firmware/1/trezor-1.10.3.bin

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
[`MEMORY_PROTECT=0`](../legacy/index.md#combining-bootloader-and-firmware-with-various-memory_protect-settings-signedunsigned)._
