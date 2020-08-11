# Bootloader for CI device tests

This bootloader always runs into bootloader mode, waits for firmware to be
uploaded, then runs the firmware.

Upon each firmware upgrade, storage is erased.

All user interaction is removed (no clicking or confirmations required)
so that it can be used in an automated way for tests.

The bootloader will run any firmware that looks "sane" (good header, hashes),
but does not check any trust flags.

Firmware must be compiled with `PRODUCTION=0` because otherwise it would
replace the bootloader and lock device.

