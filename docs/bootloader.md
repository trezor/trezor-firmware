# TREZOR Core Bootloader

TREZOR initialization in split into two stages.
See [Memory Layout](memory.md) for info about in which sectors each stage is stored.

First stage (boardloader) is stored in write-protected area, which means it is non-upgradable.
Only second stage (bootloader) update is allowed.

## First Stage - Boardloader

First stage checks the integrity and signatures of the second stage
and runs it if everything is OK.

If first stage boardloader finds a valid second stage bootloader image
on the SD card (in raw format, no filesystem), it will replace the internal
second stage, allowing a second stage update via SD card.

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

Total length of bootloader header is always 512 bytes.

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
| 0x0014 | 427    | reserved | not used yet (zeroed) |
| 0x01BF | 1      | sigmask | SatoshiLabs signature indexes (bitmap) |
| 0x01C0 | 64     | sig | SatoshiLabs aggregated signature |

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
| 0x0010 | 1      | vtrust | level of vendor trust (0-100) |
| 0x0011 | 15     | reserved | not used yet (zeroed) |
| 0x0020 | 32     | vpub1 | vendor pubkey 1 |
| ...    | ...    | ... | ... |
| ?      | 32     | vpubn | vendor pubkey n |
| ?      | 1      | vstr_len | vendor string length |
| ?      | ?      | vstr | vendor string |
| ?      | ?      | vstrpad | padding to a multiple of 4 bytes |
| ?      | ?      | vimg | vendor image (in [TOIf format](toif.md)) |
| ?      | ?      | reserved | padding to an address that is -65 modulo 512 (zeroed) |
| ?      | 1      | sigmask | SatoshiLabs signature indexes (bitmap) |
| ?      | 64     | sig | SatoshiLabs aggregated signature |

### Firmware Header

Total length of firmware header is always 512 bytes.

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
| 0x0014 | 427    | reserved | not used yet (zeroed) |
| 0x01BF | 1      | sigmask | vendor signature indexes (bitmap) |
| 0x01C0 | 64     | sig | vendor aggregated signature |

## Various ideas

* Bootloader should be able to read vendor + firmware header and send info
  about FW to client in features message.
* Bootloader should not try to run firmware if there is not any.
* Storage wiping rule: Don't erase storage when old FW and new FW are signed
  using the same key set. Otherwise erase.
* Bootloader should send error to client when firmware update fails and allow
  client to try one more time. This prevents storage area erasure by accident.
