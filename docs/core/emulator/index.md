# Emulator

Emulator is a unix version of Core firmware that runs on your computer.

![emulator](emulator.jpg)

There is neither boardloader nor bootloader and no firmware uploads. Emulator runs the current code as is it is and if you want to run some specific firmware version you need to use git for that (simply checkout the right branch/tag). Actually, maybe we should call it _simulator_ to be precise, because it does not emulate the device in its completeness, it just runs the firmware on your host.

Emulator significantly speeds up development and has several features to help you along the way.

## How to run

1. [build](../build/emulator.md) the emulator
2. run `emu.sh`
3. to use [bridge](https://github.com/trezor/trezord-go) with the emulator support, start it with `trezord -e 21324`

Now you can use the emulator the same way as you use the device, for example you can visit our Wallet (https://wallet.trezor.io), use our Python CLI tool (`trezorctl`) etc. Simply click to emulate screen touches.

## Features

### Debug mode

To allow debug link (to run tests), see exceptions and log output, run emulator with `PYOPT=0 ./emu.sh`. To properly distinguish the debug mode from production there is a tiny red square in the top right corner. The debug mode is obviously disabled on production firmwares.

![emulator](emulator-debug.png)

### Initialize with mnemonic words

If the debug mode is enabled, you can load the device with any recovery seed directly from the console. This feature is otherwise disabled. To enter seed use `trezorctl`:

```sh
trezorctl -m "your mnemonic words"
```

or to use the "all all all" seed defined in [SLIP-14](https://github.com/satoshilabs/slips/blob/master/slip-0014.md):

```sh
trezorctl -s
```

Shamir Backup is also supported:

```sh
trezorctl -m "share 1 words" -m "share 2 words"
```

### Storage and Profiles

Internal Trezor's storage is emulated and stored in the `/var/tmp/trezor.flash` file on default. Deleting this file is similar to calling _wipe device_. You can also find `/var/tmp/trezor.sdcard` for SD card and `/var/tmp/trezor.log`, which contains the communication log, the same as is in the emulator's stdout.

To run emulator with different files set the environment variable **TREZOR_PROFILE** like so:

```sh
TREZOR_PROFILE=foobar ./emu.sh
```

This will create a profile directory in your home ``` ~/.trezoremu/foobar``` containing emulator run files. Alternatively you can set a full path like so:

```sh
TREZOR_PROFILE=/var/tmp/foobar ./emu.sh
```

### Run in gdb

Running `emu.sh` with `-d` runs emulator inside gdb/lldb.

### Watch for file changes

Running `emu.sh` with `-r` watches for file changes and reloads the emulator if any occur. Note that this does not do rebuild, i.e. this works for MicroPython code (which is interpreted) but if you make C changes, you need to rebuild your self.

### Print screen

Press `p` on your keyboard to capture emulator's screen. You will find a png screenshot in the `src` directory.

### Environment Variables

#### Memory statistics

If ```TREZOR_LOG_MEMORY=1``` is set, the emulator prints memory usage information after each workflow task is finished.

#### Disable animations

```TREZOR_DISABLE_ANIMATION=1``` disables fading and other animations, which speeds up the UI workflows significantly (useful for tests). This is also requirement for UI integration tests.
