# Running UI tests

## 1. Running the full test suite

_Note: You need Pipenv, as mentioned in the core's [documentation](https://docs.trezor.io/trezor-firmware/core/) section._

In the `trezor-firmware` checkout, in the root of the monorepo, install the environment:

```sh
pipenv sync
```

And run the tests:

```sh
pipenv run make -C core test_emu_ui
```

## 2. Running tests manually

Install the pipenv environment as outlined above. Then switch to a shell inside the
environment:

```sh
pipenv shell
```

If you want to test against the emulator, run it in a separate terminal:
```sh
./core/emu.py
```

Now you can run the test suite with `pytest` from the root directory:
```sh
pytest tests/device_tests --ui=test
```

You can also skip tests marked as `skip_ui`.

```sh
pytest tests/device_tests --ui=test -m "not skip_ui"
```

# Updating Fixtures ("Recording")

The `--ui` pytest argument has two options:

- **record**: Create screenshots and calculate theirs hash for each test.
The screenshots are gitignored, but the hash is included in git.
- **test**: Create screenshots, calculate theirs hash and test the hash against
the one stored in git.

If you want to make a change in the UI you simply run `--ui=record`. An easy way
to proceed is to run `--ui=test` at first, see what tests fail (see the Reports section below),
decide if those changes are the ones you expected and then finally run the `--ui=record`
and commit the new hashes.

## Reports

Each `--ui=test` creates a clear report which tests passed and which failed.
The index file is stored in `tests/ui_tests/reports/index.html`, but for an ease of use
you will find a link at the end of the pytest summary.

On CI this report is published as an artifact.
