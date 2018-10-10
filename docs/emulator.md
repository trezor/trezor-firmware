# Emulator

![emulator](emulator.jpg)

1. [build](build.md) the emulator
2. run `emu.sh`
3. to use [bridge](https://github.com/trezor/trezord-go) with the emulator support, start it with `trezord -e 21324`

## Profiles

To run emulator with different flash and sdcard files set the environment
variable **TREZOR_PROFILE** like so:

```sh
TREZOR_PROFILE=foobar ./emu.sh
```

This will create a profile directory in your home ``` ~/.trezoremu/foobar```
containing emulator run files.

Alternatively you can set a full path like so:

```sh
TREZOR_PROFILE=/var/tmp/foobar ./emu.sh
```

When the **TREZOR_PROFILE** is not set the default is ```/var/tmp``` .
