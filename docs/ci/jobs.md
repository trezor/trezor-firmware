# List of GitLab CI Jobs

## Environment

### environment

Environment job builds the `ci/Dockerfile` and pushes the built docker image
into our GitLab registry. Since modifications of this Dockerfile are very rare
this si a _manual_ job which needs to be triggered on GitLab.

Almost all CI jobs run inside this docker image.

## Build

All builds are published as artifacts so you can download and use them.

### core fw btconly build

Build of Core into firmware. Bitcoin-only version.

### core fw regular build

Build of Core into firmware. Regular version. **Are you looking for Trezor T firmware
build? This is most likely it.**

### core fw regular debug build

Build of Core into firmware with enabled _debug_ mode. In debug mode you can
upload mnemonic seed, use debug link etc. which enables device tests. Storage
on the device gets wiped on every start in this firmware.

### core unix frozen btconly debug build

Build of Core into UNIX emulator. Something you can run on your laptop.

Frozen version. That means you do not need any other files to run it, it is just
a single binary file that you can execute directly.

See [Emulator](../core/emulator/index.md) for more info.

Debug mode enabled, Bitcoin-only version.

### core unix frozen debug build

Same as above but regular version (not only Bitcoin). **Are you looking for a Trezor T
emulator? This is most likely it.**

### core unix frozen regular build

Same as above but regular version (not only Bitcoin) without debug mode enabled.

### core unix regular build

Non-frozen emulator build. This means you still need Python files present which get
interpreted.

### crypto build

Build of our cryptographic library, which is then incorporated into the other builds.

### legacy emu btconly build

Build of Legacy into UNIX emulator. Use keyboard arrows to emulate button presses.

Bitcoin-only version.

### legacy emu regular build

Regular version (not only Bitcoin) of above. **Are you looking for a Trezor One
emulator? This is most likely it.**

### legacy fw btconly build

Build of Legacy into firmware. Bitcoin only.

### legacy fw debug build

Build of Legacy into firmware. Debug mode on. Storage on the device gets wiped on every
start in this firmware.

### legacy fw regular build

Build of Legacy into firmware. Regular version. **Are you looking for Trezor One firmware
build? This is most likely it.**

## Test

### core device ui test

UI tests for Core. See artifacts for a comprehensive report of UI. See [tests/ui-tests](../tests/ui-tests.html#reports)
for more info.

### hardware core regular device test

[Device tests](../tests/device-tests.md) that run against an actual physical Trezor T.
The device needs to have special bootloader, found in `core/embed/bootloader_ci`, that
makes it possible to flash firmware without confirmation on the touchscreen.

All hardware tests are run nightly on the `master` branch, as well as on push to branches
with whitelisted prefix. If you want hardware tests ran on your branch, make sure its
name starts with `hw/`.

### hardware core btconly device test

Also device tests on physical Trezor T but with Bitcoin-only firmware.

### hardware legacy regular device test

[Device tests](../tests/device-tests.md) executed on physical Trezor 1.
This works thanks to [tpmb](https://github.com/mmahut/tpmb), which is a small arduino
device capable of pushing an actual buttons on the device.

### hardware legacy btconly device test

Also device tests on physical Trezor 1 but with Bitcoin-only firmware.
