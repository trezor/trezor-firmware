# Tests

## Burn tests

These tests are doing a simple read/write operations on the device to see if the hardware can endure high number of flash writes. Meant to be run on the device directly for a long period of time.

## Device tests

Device tests are integration tests that can be run against either emulator or on an actual device. 
You are responsible to provide either an emulator or a device with Debug mode present.

### Device tests

The original version of device tests. These tests can be run against both Model One and Model T.

See [device-tests.md](device-tests.md) for instructions how to run it.

### UI tests

UI tests use device tests and take screenshots of every screen change and compare  them against fixtures. Currently for model T only. 

See [ui-tests.md](ui-tests.md) for more info.

### Click tests

Click tests are a next-generation of the Device tests. The tests are quite similar, but they are capable of imitating user's interaction with the screen.

## Fido tests

Implement U2F/FIDO2 tests.

## Upgrade tests

These tests test upgrade from one firmware version to another. They initialize an emulator on some specific version and then pass its storage to another version to see if the firmware operates as expected. They use fixtures from https://firmware.corp.sldev.cz/upgrade_tests/ which can be downloaded using the `download_emulators.sh` script.

See the [upgrade-tests.md](upgrade-tests.md) for instructions how to run it.

## Persistence tests

These tests test the Persistence mode, which is currently used in the device recovery. These tests launch the emulator themselves and they are capable of restarting or stopping it simulating user's plugging in or plugging out the device.
