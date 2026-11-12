# Monero tests

`make -C core test_emu_monero` runs Monero's Trezor test suite (`trezor_tests`) against the emulator.
Linux and macOS only.

The suite is built from the `vendor/monero` submodule commit (`ph4r05/monero`) with the patches in
`core/tests/monero/patches/`. CI builds it in the `monero_tests_binary` job and caches it until the
submodule commit or `core/tests/monero/` changes.

## Running locally

If `core/tests/trezor_monero_tests` is missing, `make -C core test_emu_monero` builds it first with
`core/tests/monero/build.sh` (needs git and docker). Delete it to rebuild after the submodule commit or
`core/tests/monero/` changes. `TREZOR_MONERO_TESTS_PATH` points the tests to a binary elsewhere.

A failing run is retried up to `TREZOR_MONERO_TESTS_ATTEMPTS` times (default 3).

## Changing the suite

To add a patch, check out the base commit, `git am` the existing patches, commit the change and
regenerate the series with `git format-patch` into `core/tests/monero/patches/`.

To move the base, point the submodule at the new commit (`git -C vendor/monero checkout <tag>`,
`git add vendor/monero`) and delete the patches it contains.

## Security fixes

Keep the patch only in the private repository's branch with the fix, never in a public fork or its CI.
Move it to the fork and the base after disclosure.
