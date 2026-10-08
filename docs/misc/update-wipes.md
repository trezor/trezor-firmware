# Firmware update and device wipe

This document describes under which circumstances the device gets wiped during a firmware
update.

## Trezor 1

The device gets **wiped**:
- If the firmware to be installed is unsigned.
- If the present firmware is unsigned.
- If the firmware to be installed has lower version than the current firmware's
_fix_version_ [1].

The device gets **wiped on every reboot**:
- If the firmware's debug mode is turned on.

## Trezor T

In Trezor T this works a bit differently, we have introduced so-called vendors headers.
Each firmware has its vendor header and this vendor header is signed by SatoshiLabs. The
actual firmware is signed by the vendor header's key. That means that all firmwares are
signed by _someone_ to be able to run on Trezor T.

We currently have two vendors:

1. SatoshiLabs
2. UNSAFE DO NOT USE

As the names suggest, the first one is the official SatoshiLabs vendor header and all
public firmwares are signed with that. The second one is meant for generic audience; if
you build firmware this vendor header is automatically applied and the firmware is signed
with it (see `core/tools/headertool.py`).

The device gets **wiped**:
- If the firmware to be installed is from different vendor than the present firmware [2].
- If the firmware to be installed has lower version than the current firmware's
_fix_version_ [1].

The device gets **wiped on every reboot**:
- If the firmware's debug mode is turned on.

----

[1] Firmware contains a _fix_version_, which is the lowest version to which that
particular firmware can be downgraded without wiping storage. It is bumped in two cases:

- The internal storage format changes in a way that older firmware would not understand.
  For example, version 2.2.0 introduced Wipe Code, which changed the storage format in a
  way that older firmwares (e.g. 2.1.8) could not handle.
- The firmware fixes a vulnerability that an attacker in possession of the device could
  exploit against data in the device's storage area without further interaction from the
  owner, e.g. a side channel leaking the seed. Whether the attacker also needs to know
  the PIN is irrelevant. Vulnerabilities that depend on the owner continuing to use the
  downgraded device do not warrant a bump, because a wipe would only make the owner
  recover the seed onto the same vulnerable firmware.

A fix_version bump is accompanied by a bump of the minor version.

[2] The most common example is if you have a device with the official firmware
(SatoshiLabs) and you install the unofficial (UNSIGNED) firmware -> the device gets
wiped. Same thing vice versa.
