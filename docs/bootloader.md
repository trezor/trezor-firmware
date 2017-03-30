# TREZOR Core Bootloader

TREZOR initialization in split into two stages. See [Memory Layout](memory.md) for info about in which sectors each stage is stored.

First stage (bootloader) is stored in write-protected area, which means it is non-upgradable.
Only second stage (loader) update is allowed.

## First Stage - Bootloader

First stage checks the integrity and signatures of the second stage and runs it if everything is OK.

If first stage bootloader finds a valid second stage loader image on the SD card (in raw format, no filesystem),
it will replace the internal second stage, allowing a second stage update via SD card.

## Second Stage - Loader

Second stage checks the integrity and signatures of the firmware and runs it if everything is OK.

If second stage loader detects a pressed finger on the display or there is no firmware loaded in the device,
it will start in a firmware update mode, allowing a firmware update via USB.

## Common notes

* Hash function used for computing data digest for signatures is BLAKE2s.
* Signature system is Ed25519 (allows combining signatures by multiple keys into one).
* All multibyte integer values are little endian.
* There is a tool called [binctl](../tools/binctl) which checks validity of the loader/firmware images including their headers.

## Loader Format

TREZOR Core (second stage) loader consists of 2 parts:

1. loader header
2. loader code

### Loader Header

Total length of loader header is always 256 bytes.

| offset | length | name | description |
|-------:|-------:|------|-------------|
| 0x0000 | 4      | magic | firmware magic `TRZL` |
| 0x0004 | 4      | hdrlen | length of the loader header |
| 0x0008 | 4      | expiry | valid until timestamp (0=infinity) |
| 0x000C | 4      | codelen | length of the loader code (without the header) |
| 0x0010 | 1      | vmajor | version (major) |
| 0x0011 | 1      | vminor | version (minor) |
| 0x0012 | 1      | vpatch | version (patch) |
| 0x0013 | 1      | vbuild | version (build) |
| 0x0014 | 171    | reserved | not used yet (zeroed) |
| 0x00BF | 1      | sigidx | SatoshiLabs signature indexes (bitmap) |
| 0x00C0 | 64     | sig | SatoshiLabs signature |

## Firmware Format

TREZOR Core firmware consists of 3 parts:

1. vendor header
2. firmware header
3. firmware code

### Vendor Header

Total length of vendor header is 84 + 32 * (number of pubkeys) + (length of vendor string) + (length of vendor image) bytes rounded up to the closest multiply of 256 bytes.

| offset | length | name | description |
|-------:|-------:|------|-------------|
| 0x0000 | 4      | magic | firmware magic `TRZV` |
| 0x0004 | 4      | hdrlen | length of the vendor header |
| 0x0008 | 4      | expiry | valid until timestamp (0=infinity) |
| 0x000C | 1      | vmajor | version (major) |
| 0x000D | 1      | vminor | version (minor) |
| 0x000E | 1      | vsig_m | number of signatures needed to run the firmware from this vendor |
| 0x000F | 1      | vsig_n | number of different pubkeys vendor provides for signing |
| 0x0010 | 32     | vpub1 | vendor pubkey 1 |
| ...    | ...    | ... | ... |
| ?      | 32     | vpubn | vendor pubkey n |
| ?      | 1      | vstr_len | vendor string length |
| ?      | ?      | vstr | vendor string |
| ?      | 2      | vimg_len | vendor image length |
| ?      | ?      | vimg | vendor image (in [TOIf format](toif.md)) |
| ?      | 1      | sigidx | SatoshiLabs signature indexes (bitmap) |
| ?      | 64     | sig | SatoshiLabs signature |

### Firmware Header

Total length of firmware header is always 256 bytes.

| offset | length | name | description |
|-------:|-------:|------|-------------|
| 0x0000 | 4      | magic | firmware magic `TRZF` |
| 0x0004 | 4      | hdrlen | length of the firmware header |
| 0x0008 | 4      | expiry | valid until timestamp (0=infinity) |
| 0x000C | 4      | codelen | length of the firmware code (without the header) |
| 0x0010 | 1      | vmajor | version (major) |
| 0x0011 | 1      | vminor | version (minor) |
| 0x0012 | 1      | vpatch | version (patch) |
| 0x0013 | 1      | vbuild | version (build) |
| 0x0014 | 171    | reserved | not used yet (zeroed) |
| 0x00BF | 1      | sigidx | vendor signature indexes (bitmap) |
| 0x00C0 | 64     | sig | vendor signature |

## Various ideas

* Loader should be able to read vendor + firmware header and send info about FW to client in features message.
* Loader should not try to run firmware if there is not any.
* Storage wiping rule: Don't erase storage when old FW and new FW are signed using the same key set. Otherwise erase.
* Loader should send error to client when firmware update fails and allow client to try one more time. This prevents storage area erasure by accident.
