# Running Upgrade Tests

1. As always, use pipenv environment:

```sh
pipenv shell
```

2. Download the emulators, if you have not already:

```sh
tests/download_emulators.sh
```

3. And run the tests using pytest:

```sh
pytest tests/upgrade_tests
```

----

You can use `TREZOR_UPGRADE_TEST` environment variable if you would like to run core or legacy upgrade tests exclusively. This will run `core` only:

```sh
TREZOR_UPGRADE_TEST="core" pytest tests/upgrade_tests
```
