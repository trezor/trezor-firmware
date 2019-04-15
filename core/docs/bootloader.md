# TREZOR Core Bootloader

TREZOR initialization is split into two stages.
See [Memory Layout](memory.md) for info about in which sectors each stage is stored.

First stage (boardloader) is stored in write-protected area, which means it is non-upgradable.
Only second stage (bootloader) update is allowed.

## First Stage - Boardloader

First stage checks the integrity and signatures of the second stage
and runs it if everything is OK.

If first stage boardloader finds a valid second stage bootloader image
on the SD card (in raw format, no filesystem), it will replace the internal
second stage, allowing a second stage update via SD card.

The boardloader is special in that it is the device's write protected embedded code.
The primary purpose for write protecting the boardloader is to make it the
immutable portion that can defend against code-based attacks (e.g.- BadUSB)
and bugs that would reprogram any/all of the embedded code.
It assures that only verified signed embedded code is run on the device
(and that the intended code is run, and not skipped).
The write protection also provides some defense against attacks where the
attacker has physical control of the device.

The boardloader must include an update mechanism for later stage code because
if it did not, then a corruption/erasure of later stage flash memory would
leave the device unusable (only the boardloader could run and it would not
pass execution to a later stage that fails signature validation).

Developer note:

A microSD card can be prepared with the following. Note that the bootloader is allocated 128 KiB.

WARNING: Ensure that you want to overwrite and destroy the contents of `/dev/mmcblk0` before running these commands.
Likewise, `/dev/mmcblk0` may be replaced by your own specific destination.

 1. `sudo dd if=/dev/zero of=/dev/mmcblk0 bs=512 count=256 conv=fsync`

 1. `sudo dd if=build/bootloader/bootloader.bin of=/dev/mmcblk0 bs=512 conv=fsync`

## Second Stage - Bootloader

Second stage checks the integrity and signatures of the firmware and runs
it if everything is OK.

If second stage bootloader detects a pressed finger on the display or there
is no firmware loaded in the device, it will start in a firmware update mode,
allowing a firmware update via USB.

## Common notes

* Hash function used for computing data digest for signatures is BLAKE2s.
* Signature system is Ed25519 (allows combining signatures by multiple keys
  into one).
* All multibyte integer values are little endian.
* There is a tool called [binctl](../tools/binctl) which checks validity
  of the bootloader/firmware images including their headers.

## Bootloader Format

TREZOR Core (second stage) bootloader consists of 2 parts:

1. bootloader header
2. bootloader code

### Bootloader Header

Total length of bootloader header is always 1024 bytes.

| offset | length | name | description |
|-------:|-------:|------|-------------|
| 0x0000 | 4      | magic | firmware magic `TRZB` |
| 0x0004 | 4      | hdrlen | length of the bootloader header |
| 0x0008 | 4      | expiry | valid until timestamp (0=infinity) |
| 0x000C | 4      | codelen | length of the bootloader code (without the header) |
| 0x0010 | 1      | vmajor | version (major) |
| 0x0011 | 1      | vminor | version (minor) |
| 0x0012 | 1      | vpatch | version (patch) |
| 0x0013 | 1      | vbuild | version (build) |
| 0x0014 | 1      | fix_vmajor | version of last critical bugfix (major) |
| 0x0015 | 1      | fix_vminor | version of last critical bugfix (minor) |
| 0x0016 | 1      | fix_vpatch | version of last critical bugfix (patch) |
| 0x0017 | 1      | fix_vbuild | version of last critical bugfix (build) |
| 0x0018 | 8      | reserved | not used yet (zeroed) |
| 0x0020 | 32     | hash1 | hash of the first code chunk (128 - 1 KiB), this excludes the header |
| 0x0040 | 32     | hash2 | hash of the second code chunk (128 KiB), zeroed if unused |
| ...    | ...    | ... | ... |
| 0x0200 | 32     | hash16 | hash of the last possible code chunk (128 KiB), zeroed if unused |
| 0x0220 | 415    | reserved | not used yet (zeroed) |
| 0x03BF | 1      | sigmask | SatoshiLabs signature indexes (bitmap) |
| 0x03C0 | 64     | sig | SatoshiLabs aggregated signature of the bootloader header |

## Firmware Format

TREZOR Core firmware consists of 3 parts:

1. vendor header
2. firmware header
3. firmware code

### Vendor Header

Total length of vendor header is 84 + 32 * (number of pubkeys) +
(length of vendor string rounded up to multiple of 4) +
(length of vendor image) bytes rounded up to the closest multiple
of 512 bytes.

| offset | length | name | description |
|-------:|-------:|------|-------------|
| 0x0000 | 4      | magic | firmware magic `TRZV` |
| 0x0004 | 4      | hdrlen | length of the vendor header (multiple of 512) |
| 0x0008 | 4      | expiry | valid until timestamp (0=infinity) |
| 0x000C | 1      | vmajor | version (major) |
| 0x000D | 1      | vminor | version (minor) |
| 0x000E | 1      | vsig_m | number of signatures needed to run the firmware from this vendor |
| 0x000F | 1      | vsig_n | number of different pubkeys vendor provides for signing |
| 0x0010 | 2      | vtrust | level of vendor trust (bitmap) |
| 0x0012 | 14     | reserved | not used yet (zeroed) |
| 0x0020 | 32     | vpub1 | vendor pubkey 1 |
| ...    | ...    | ... | ... |
| ?      | 32     | vpubn | vendor pubkey n |
| ?      | 1      | vstr_len | vendor string length |
| ?      | ?      | vstr | vendor string |
| ?      | ?      | vstrpad | padding to a multiple of 4 bytes |
| ?      | ?      | vimg | vendor image (120x120 pixels in [TOIf format](toif.md)) |
| ?      | ?      | reserved | padding to an address that is -65 modulo 512 (zeroed) |
| ?      | 1      | sigmask | SatoshiLabs signature indexes (bitmap) |
| ?      | 64     | sig | SatoshiLabs aggregated signature of the vendor header |

#### Vendor Trust

Vendor trust is stored as bitmap where unset bit means the feature is active.

| bit | hex    | meaning                                 |
|-----|--------|-----------------------------------------|
|  0  | 0x0001 | wait 1 second                           |
|  1  | 0x0002 | wait 2 seconds                          |
|  2  | 0x0004 | wait 4 seconds                          |
|  3  | 0x0008 | wait 8 seconds                          |
|  4  | 0x0010 | use red background instead of black one |
|  5  | 0x0020 | require user click                      |
|  6  | 0x0040 | show vendor string (not just the logo)  |

### Firmware Header

Total length of firmware header is always 1024 bytes.

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
| 0x0014 | 1      | fix_vmajor | version of last critical bugfix (major) |
| 0x0015 | 1      | fix_vminor | version of last critical bugfix (minor) |
| 0x0016 | 1      | fix_vpatch | version of last critical bugfix (patch) |
| 0x0017 | 1      | fix_vbuild | version of last critical bugfix (build) |
| 0x0018 | 8      | reserved | not used yet (zeroed) |
| 0x0020 | 32     | hash1 | hash of the first code chunk (128 - 1 KiB), this excludes the header |
| 0x0040 | 32     | hash2 | hash of the second code chunk (128 KiB), zeroed if unused |
| ...    | ...    | ... | ... |
| 0x0200 | 32     | hash16 | hash of the last possible code chunk (128 KiB), zeroed if unused |
| 0x0220 | 415    | reserved | not used yet (zeroed) |
| 0x03BF | 1      | sigmask | vendor signature indexes (bitmap) |
| 0x03C0 | 64     | sig | vendor aggregated signature of the firmware header |
