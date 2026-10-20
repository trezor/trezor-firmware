# Bootloader tests

Bootloader tests run the bootloader emulator, one run per test, and drive it the
way the click tests drive firmware: input over the debug link, host messages over
the wire port, screenshots hashed against `tests/ui_tests/fixtures.json`.

Unlike the firmware emulator, a bootloader run is expected to end on its own. A
test starts the emulator with explicit startup parameters (a firmware image to
preload, a boot command, a record directory), interacts with it, and then reads
how the run ended: the process exit code tells the kind of exit, the file
`trezor.bootargs` in the profile directory tells which boot command the
bootloader left for the next boot, and the flash file tells whether storage
survived. See `trezorlib._internal.bootloader_emulator` for the wrapper and
`trezorlib._internal.bootargs` for the decoders.

## Running

Build a debuglink bootloader emulator with the development keys, then run the
suite:

```sh
make -C core build_bootloader_emu PYOPT=0 BOOTLOADER_DEVEL=1 TREZOR_MODEL=T3T1
make -C core test_emu_bootloader       # plain
make -C core test_emu_bootloader_ui    # with UI fixtures
```

The binary is taken from `core/build/artifacts/latest/bootloader-emu`, or from
the path in `TREZOR_BOOTLOADER_EMU`.

To record fixtures for a model, run with `--ui=record`:

```sh
cd tests
TREZOR_BOOTLOADER_EMU=../core/build/artifacts/T3T1/bootloader-emu pytest bootloader_tests --ui=record
```

With `--ui` the screens are recorded from the first frame of every run, so the
boot screens are part of the fixtures.

## Writing a test

Use the `bootloader` fixture. `bootloader.start(BootloaderStartup(...))` starts a
run and returns the emulator; its `client` carries the debug link (`debug`) and
the wire channel (`wire`). A wire call that needs an on-screen confirmation is
made with `wire.call_in_background()` while the test clicks through the screen.
Finish with `bootloader.wait_exit()` for a run that ends by itself, or
`bootloader.abort()` for a screen that waits for the user to reconnect the
device. Both return an `ExitRecord` with `kind`, `bootargs` and
`storage_erased`.

The bootloader emulator prints its flash layout with `-p` and takes a boot
command from a file with `-B`; `BootArgs.wipe(...)`, `BootArgs.show_rsod(...)`
and friends build such files.
