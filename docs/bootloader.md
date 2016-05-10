#TREZOR OS Bootloader

All multibyte integer values are little endian!

##Firmware File Format

TREZOR OS firmware file consists of 3 parts:

1. vendor header
2. firmware header
3. firmware code

###Vendor Header

| offset | length | name | description |
|-------:|-------:|------|-------------|
| 0x0000 | 4      | magic | firmware magic `TRZV` |
| 0x0004 | 4      | hlen | length of the vendor header |
| 0x0008 | 4      | expiry | valid until timestamp |
| 0x000C | 1      | vsig_m | number of signatures needed to run the firmware from this vendor |
| 0x000D | 1      | vsig_n | number of pubkeys vendor wants to use for signing |
| 0x000E | 1      | vstr_len | vendor string length |
| 0x000F | ?      | vstr | vendor string |
| ?      | ?      | vimg | vendor image (in [TOIf format](toif.md)) |
| ?      | 32     | vpub1 | vendor pubkey 1 |
| ...    | ...    | ... | ... |
| ?      | 32     | vpubn | vendor pubkey n |
| ?      | 1      | slsigidx | SatoshiLabs signature indexes |
| ?      | 64     | slsig | SatoshiLabs signature |

###Firmware Header

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
| 0x0014 | 1      | vidx   | vendor signature indexes |
| 0x0015 | 64     | vsign  | vendor signature |
