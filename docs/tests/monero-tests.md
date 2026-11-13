# Monero tests

`make -C core test_emu_monero` runs Monero's Trezor test suite (`trezor_tests`) against the emulator.
Linux and macOS only.

The suite is built from the `vendor/monero` submodule commit (`ph4r05/monero`) with the patches in
`core/tests/monero/patches/` by `core/tests/monero/build.sh`. Those three are the build inputs,
identified by `core/tests/monero/inputs.sh`. CI builds the suite in the `monero_tests_binary` job only
when the inputs change, caches it and uploads it as the `monero-tests-<inputs ID>` artifact.

## Running locally

The tests need an emulator built with debuglink. CI runs them on T2T1, T3B1 and T3T1:

```sh
xtask build firmware --emulator -m T3T1 -p test
make -C core test_emu_monero
```

Before starting the emulator, `make` checks the binary at `core/tests/trezor_monero_tests`
(`TREZOR_MONERO_TESTS_PATH` to use another path). If it is missing or was built from other inputs, it
asks whether to:

- **download** the binary CI built from the same inputs (`core/tests/monero/download.sh`). Needs
  `gh auth login`. CI keeps the artifact for 7 days after the last run with these inputs, nightly runs
  keep the one for `main` available.
- **build** it (`core/tests/monero/build.sh`). Needs git and docker, with your user allowed to use the
  docker daemon (in the `docker` group, log in again after adding it). Takes about 30 minutes.
- **keep** the outdated binary.

Without a terminal, set the choice in `TREZOR_MONERO_TESTS_GET=download|build|keep`, e.g.
`TREZOR_MONERO_TESTS_GET=download make -C core test_emu_monero`.

On its first run, the binary generates a test chain and keeps it next to itself as
`<binary>.chain`. Building or downloading a new binary deletes it. `make -C core clean_monero` deletes
the binary with its test chain and logs, `docker rmi monero-trezor-tests` the image of a local build.

`make` starts a temporary headless emulator on the default UDP port 21324, so do not run it while
another emulator uses that port. The output goes to `core/tests/trezor_monero_tests.log`. A failing
run is retried up to `TREZOR_MONERO_TESTS_ATTEMPTS` times (default 3); all attempts are kept in the
log.

## Changing the suite

To add a patch, check out the base commit, `git am` the existing patches, commit the change and
regenerate the series with `git format-patch` into `core/tests/monero/patches/`.

To move the base, point the submodule at the new commit (`git -C vendor/monero checkout <tag>`,
`git add vendor/monero`) and delete the patches it contains.

## Security fixes

Keep the patch only in the private repository's branch with the fix, never in a public fork or its CI.
Move it to the fork and the base after disclosure.
