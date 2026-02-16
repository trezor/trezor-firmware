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

3. And run the tests using pytest:

```sh
pytest tests/upgrade_tests
```

----

You can use `TREZOR_UPGRADE_TEST` environment variable if you would like to run core or legacy upgrade tests exclusively. For core, pick a specific model:

```sh
TREZOR_UPGRADE_TEST="core-t2t1" pytest tests/upgrade_tests
```

To run T3W1 only:

```sh
TREZOR_UPGRADE_TEST="core-t3w1" pytest tests/upgrade_tests
```

## Tropic-Enabled Emulators

For models that support Tropic (like T3W1), two sets of emulators can coexist:
- Regular emulators (tropic disabled): `tests/emulators/T3W1/`
- Tropic-enabled emulators: `tests/emulators/T3W1/T3W1_tropic_on/`

The **upgrade test framework automatically detects** which variant to use:
- If tropic-enabled emulators exist in the `T3W1_tropic_on` subdirectory, they are used
- Otherwise, regular emulators are used as fallback

No additional configuration is needed - just download the emulators you want to test with.

**Note:** This auto-detection is specific to upgrade tests. Other test suites (like device_tests) 
will use regular emulators by default for faster execution, as they don't require tropic functionality.
