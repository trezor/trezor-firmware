# Running Upgrade Tests

1. As always, use `nix-shell` + `uv` environment:

```sh
nix-shell
uv sync
source .venv/bin/activate
```

2. Download the emulators for the models you want to test, if you have not already:

```sh
tests/download_emulators.sh {model}
```

For tropic-capable models, this also downloads tropic-enabled emulator variants into the same subfolder layout as on S3.

3. Build the emulator for the model you want to test, use `DISABLE_TROPIC=0` for tropic-enabled models:

```sh
make -C core build_unix TREZOR_MODEL=T2T1
make -C core build_unix TREZOR_MODEL=T3W1 DISABLE_TROPIC=0
```

4. And run the tests using pytest:

```sh
pytest tests/upgrade_tests
```

----

You can use `TREZOR_UPGRADE_TEST` to limit the run to specific models.
Accepted values are model internal names (`T1B1`, `T2T1`, `T3W1`), and they can be combined as a comma-separated list.

```sh
TREZOR_UPGRADE_TEST="T2T1" pytest tests/upgrade_tests
TREZOR_UPGRADE_TEST="T3W1" pytest tests/upgrade_tests
TREZOR_UPGRADE_TEST="T1B1,T3W1" pytest tests/upgrade_tests
```

If `TREZOR_UPGRADE_TEST` is not set, this command auto-selects targets based on locally available emulator builds.
`T1B1` (legacy) runs when the local legacy emulator is available, and `T2T1`/`T3W1` (core) runs when the local core emulator is available.
For local core builds, the suite detects the model from the build tree; if it cannot be determined, the run fails explicitly and you should set `TREZOR_UPGRADE_TEST` yourself.
