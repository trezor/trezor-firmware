# Running Upgrade Tests

1. As always, use uv environment:

```sh
uv sync
source .venv/bin/activate
```

2. Download the emulators for the models you want to test, if you have not already:

```sh
tests/download_emulators.sh {model}
```

For tropic-capable models, this also downloads tropic-enabled emulator variants into the same subfolder layout as on S3.

3. And run the tests using pytest:

```sh
pytest tests/upgrade_tests
```

If `TREZOR_UPGRADE_TEST` is not set, this command auto-selects targets based on locally available emulator builds.
`legacy` runs when the local legacy emulator is available, and `core` runs when the local core emulator is available.
For local core builds, the suite detects whether the build is `core-t2t1` or `core-t3w1` from the build tree; if the model cannot be determined, the run fails explicitly and you should set `TREZOR_UPGRADE_TEST` yourself.

----

You can use `TREZOR_UPGRADE_TEST` to limit the run to specific upgrade-test targets.
Accepted values are `legacy`, `core-t2t1`, and `core-t3w1`, and they can be combined as a comma-separated list.

```sh
TREZOR_UPGRADE_TEST="core-t2t1" pytest tests/upgrade_tests
TREZOR_UPGRADE_TEST="core-t3w1" pytest tests/upgrade_tests
TREZOR_UPGRADE_TEST="legacy,core-t3w1" pytest tests/upgrade_tests
```
