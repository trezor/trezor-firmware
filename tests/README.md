# Tests

## Burn tests

These tests are doing a simple read/write operations on the device to see if the hardware can endure high number of flash writes. Meant to be run on the device directly for a long period of time.

## Device tests

Device tests are integration tests that can be run against either emulator or on an actual device. The Debug mode is required. These tests can be run against both Model One and Model T.

See the [README](device_tests/README.md) for instructions how to run it.

## Fido tests

Implement U2F/FIDO2 tests.

## Upgrade tests

These tests test upgrade from one firmware version to another. They initialize an emulator on some specific version and then pass its storage to another version to see if the firmware operates as expected. They use fixtures from https://firmware.corp.sldev.cz/upgrade_tests/ which can be downloaded using the `download_emulators.sh` script.

See the [README](upgrade_tests/README.md) for instructions how to run it.
