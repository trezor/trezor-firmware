#TREZOR Core Bootloader

All multibyte integer values are little endian!

##Firmware File Format

TREZOR Core firmware file consists of 3 parts:

1. vendor header
2. firmware header
3. firmware code

Hash function used is SHA-256 and signature system is Ed25519 (allows combining signatures by multiple keys into one).

###Vendor Header

Total length of vendor header is 82 + 32 * (number of pubkeys) + (length of vendor string) + (length of vendor image) bytes rounded up to the closest multiply of 256 bytes.

| offset | length | name | description |
|-------:|-------:|------|-------------|
| 0x0000 | 4      | magic | firmware magic `TRZV` |
| 0x0004 | 4      | hlen | length of the vendor header |
| 0x0008 | 4      | expiry | valid until timestamp |
| 0x000C | 1      | vsig_m | number of signatures needed to run the firmware from this vendor |
| 0x000D | 1      | vsig_n | number of pubkeys vendor wants to use for signing |
| 0x000E | 2      | reserved | not used yet |
| 0x0010 | 32     | vpub1 | vendor pubkey 1 |
| ...    | ...    | ... | ... |
| ?      | 32     | vpubn | vendor pubkey n |
| ?      | 1      | vstr_len | vendor string length |
| ?      | ?      | vstr | vendor string |
| ?      | ?      | vimg | vendor image (in [TOIf format](toif.md)) |
| ?      | 1      | slsigidx | SatoshiLabs signature indexes (bitmap) |
| ?      | 64     | slsig | SatoshiLabs signature |

###Firmware Header

Total length of firmware header is 256 bytes.

| offset | length | name | description |
|-------:|-------:|------|-------------|
| 0x0000 | 4      | magic | firmware magic `TRZF` |
| 0x0004 | 4      | hlen | length of the firmware header |
| 0x0008 | 4      | expiry | valid until timestamp |
| 0x000C | 4      | codelen | length of the firmware code |
| 0x0010 | 1      | vmajor | version (major) |
| 0x0011 | 1      | vminor | version (minor) |
| 0x0012 | 1      | vpatch | version (patch) |
| 0x0013 | 1      | vbuild | version (build) |
| 0x0014 | 1      | vndsigidx | vendor signature indexes (bitmap) |
| 0x0015 | 64     | vndsig | vendor signature |
| 0x0079 | 135    | reserved | not used yet |

##Various ideas

* Bootloader should be able to read vendor+firmware header and send info about FW to client in features message.
* Bootloader should not try to run firmware if there is not any.
* Storage wiping rule: Don't erase storage when old FW and new FW are signed using the same key set. Otherwise erase.
* Bootloader should send error to client when firmware update fails and allow client to try one more time. This prevents storage area erasure by accident.
