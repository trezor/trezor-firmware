# hid-bridge

Creates a virtual hid device which can be controlled by a user driver via a UDP port.

## Installation

You need Python 3.5 or higher.

The uhid driver is required. If it is built as a module and not loaded, load it by `modprobe uhid`.

You must have read/write permission to the `/dev/uhid/` device as well as to the newly created `/dev/hidraw*` device. This may be accomplished by copying `50-hid-bridge.rules` into `/etc/udev/rules.d/`. You may need to reload the driver afterwards.

## Usage

Run [Trezor emulator](https://github.com/trezor/trezor-core/blob/master/docs/emulator.md) and `./hid-bridge`.

## Known issues

It does not work with some older versions of Firefox. Firefox used to close hid devices upon loss of focus.

It does not work with the emulator in debug mode since the emulator doesn't start the hid interface in debug mode.
