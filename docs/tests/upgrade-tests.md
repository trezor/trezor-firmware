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
