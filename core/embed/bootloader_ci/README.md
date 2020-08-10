# Bootloader for CI device tests

This bootloader always runs into bootloader mode, waits for firmware to be
uploaded, then runs the firmware.

Firmware must be compiled with `PRODUCTION=0` because otherwise it would
replace the bootloader and lock device.

