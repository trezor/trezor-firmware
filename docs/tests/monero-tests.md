# Monero tests

`make -C core test_emu_monero` runs Monero's Trezor test suite (`trezor_tests`) against the emulator.
Linux and macOS only.

The suite is built from the `ph4r05/monero` commit pinned in `core/tests/monero/build.sh` with the
patches in `core/tests/monero/patches/`. CI builds it in the `monero_tests_binary` job and caches it
until `core/tests/monero/` changes.

## Running locally

The tests need an emulator built with debuglink. CI runs them on T2T1, T3B1 and T3T1:

```sh
xtask build firmware --emulator -m T3T1 -p test
```

Build the suite and run it. The build needs git and docker, with your user allowed to use the docker
daemon (in the `docker` group):

```sh
core/tests/monero/build.sh /tmp/monero-tests
TREZOR_MONERO_TESTS_PATH=/tmp/monero-tests/trezor_tests make -C core test_emu_monero
```

Instead of building it, you can download the suite from a CI run whose `vendor/monero` commit and
`core/tests/monero/` match your checkout (the `monero-tests` artifact of the `Core` workflow):

```sh
gh run download <run-id> -R trezor/trezor-firmware -n monero-tests -D /tmp/monero-tests
TREZOR_MONERO_TESTS_PATH=/tmp/monero-tests/trezor_tests make -C core test_emu_monero
```

`make` starts a temporary headless emulator on the default UDP port 21324, so do not run it while
another emulator uses that port. The output goes to `core/tests/trezor_monero_tests.log`. A failing
run is retried up to `TREZOR_MONERO_TESTS_ATTEMPTS` times (default 3); all attempts are kept in the
log.

## Changing the suite

To add a patch, check out the base commit, `git am` the existing patches, commit the change and
regenerate the series with `git format-patch` into `core/tests/monero/patches/`.

To move the base, set `BASE_URL` and `BASE_COMMIT` in `build.sh` and delete the patches it contains.

## Security fixes

Keep the patch only in the private repository's branch with the fix, never in a public fork or its CI.
Move it to the fork and the base after disclosure.
