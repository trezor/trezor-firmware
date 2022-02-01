# Trezor One firmware format

Historically Trezor One has been using 256-byte header (w/ `TRZR` magic string) followed by the
actual firmware. Since version 1.8.0, different 1024-byte header (w/ `TRZF` magic string) is in use,
and building firmware from this repository produces firmware image containing such header followed
by firmware code.

Official release firmware contains both these headers for compatibility with old bootloaders. That
means there is a 256-byte `TRZR` header followed by 1024-byte `TRZF` header followed by code.

* Hash function used for computing data digest for signatures is SHA256.
* Signature system is ECDSA over SECP256k1.
* All multibyte integer values are little endian.

## Legacy Header

Total length of legacy header is always 256 bytes.

| offset | length | name | description |
|-------:|-------:|------|-------------|
| 0x0000 | 4      | magic | firmware magic `TRZR` |
| 0x0004 | 4      | codelen | length of V2 header + code (length of code before 1.8.0) |
| 0x0008 | 1      | sigindex1 | index of key for `sig1` |
| 0x0009 | 1      | sigindex2 | index of key for `sig2` |
| 0x000A | 1      | sigindex3 | index of key for `sig3` |
| 0x000B | 1      | flags | unused since 1.8.0 (zeroed) |
| 0x000C | 52     | reserved | not used yet (zeroed) |
| 0x0040 | 64     | sig1 | signature #1 |
| 0x0080 | 64     | sig2 | signature #2 |
| 0x00C0 | 64     | sig3 | signature #3 |

Signature verification:

* Calculate SHA256 digest of firmware without this header.
* Verify signature `sig1` of the digest against public key with index `sigindex1` in [`V1_BOOTLOADER_KEYS`](../../../python/src/trezorlib/firmware.py).
* Repeat for `sig2` and `sig3`. Indexes must be distinct.

## V2 Header

This header has the same format as [Model T Firmware Header](../model-t/boot.md#firmware-header),
however due to different signature scheme the `sigmask` and `sig` fields are zeroed and part of the
reserved space is used for T1-specific fields `sig1`-`sig3`, `sigindex1-sigindex3`. Total length of
v2 header is always 1024 bytes.

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
| 0x0020 | 32     | hash1 | hash of the first code chunk excluding both the legacy and the v2 header (129792 B) |
| 0x0040 | 32     | hash2 | hash of the second code chunk (128 KiB), zeroed if unused |
| ...    | ...    | ... | ... |
| 0x0200 | 32     | hash16 | hash of the last possible code chunk (128 KiB), zeroed if unused |
| 0x0220 | 64     | sig1 | signature #1 |
| 0x0260 | 64     | sig2 | signature #2 |
| 0x02A0 | 64     | sig3 | signature #3 |
| 0x02E0 | 1      | sigindex1 | index of key for `sig1` |
| 0x02E1 | 1      | sigindex2 | index of key for `sig2` |
| 0x02E2 | 1      | sigindex3 | index of key for `sig3` |
| 0x02E3 | 220    | reserved | not used yet (zeroed) |
| 0x03BF | 1      | reserved_sigmask | unused in T1 (zeroed) |
| 0x03C0 | 64     | reserved_sig | unused in T1 (zeroed) |

Signature verification:

* Calculate SHA256 digest of the entire header with `sig1`-`sig3` and `sigindex1`-`sigindex3` zeroed
  out.
* Verify signature `sig1` of the digest against public key with index `sigindex1` in [`V1_BOOTLOADER_KEYS`](../../../python/src/trezorlib/firmware.py).
* Repeat for `sig2` and `sig3`. Indexes must be distinct.
