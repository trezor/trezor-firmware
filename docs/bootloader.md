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
| 0x0008 | 1      | vsig_m | number of signatures needed to run the firmware from this vendor |
| 0x0009 | 1      | vsig_n | number of pubkeys vendor wants to use for signing |
| 0x000A | 1      | vstr_len | vendor string length |
| 0x000B | ?      | vstr | vendor string |
| ?      | ?      | vimg | vendor image (in [TOIf format](toif.md)) |
| ?      | 32     | vpub1 | vendor pubkey 1 |
| ...    | ...    | ... | ... |
| ?      | 32     | vpubn | vendor pubkey n |
| ?      | 64     | slsig1 | SatoshiLabs signature 1 |
| ?      | 64     | slsig2 | SatoshiLabs signature 2 |
| ?      | 64     | slsig3 | SatoshiLabs signature 3 |

###Firmware Header

| offset | length | name | description |
|-------:|-------:|------|-------------|
| 0x0000 | 4      | magic | firmware magic `TRZF` |
| 0x0004 | 4      | hlen | length of the firmware header |
| 0x0008 | 4      | codelen | length of the firmware code |
| 0x000C | 1      | vmajor | version (major) |
| 0x000D | 1      | vminor | version (minor) |
| 0x000E | 1      | vpatch | version (patch) |
| 0x000F | 1      | vbuild | version (build) |
| 0x0010 | 1      | vidx1 | vendor signature index 1 |
| 0x0011 | 32     | vsig1 | vendor signature 1 |
| 0x0043 | 1      | vidx2 | vendor signature index 2 |
| 0x0044 | 32     | vsig2 | vendor signature 2 |
| ...    | ...    | ...   | ... |
| ?      | 1      | vidxn | vendor signature index n |
| ?      | 32     | vsign | vendor signature n |
