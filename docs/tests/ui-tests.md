# Running UI tests

## 1. Running the full test suite

_Note: You need Poetry, as mentioned in the core's [documentation](https://docs.trezor.io/trezor-firmware/core/) section._

In the `trezor-firmware` checkout, in the root of the monorepo, install the environment:

```sh
poetry install
```

And run the tests:

```sh
poetry run make -C core test_emu_ui
```

## 2. Running tests manually

Install the poetry environment as outlined above. Then switch to a shell inside the
environment:

```sh
poetry shell
```

If you want to test against the emulator, run it with disabled animation in a separate terminal:
```sh
./core/emu.py -a
```

Now you can run the test suite with `pytest` from the root directory:
```sh
pytest tests/device_tests --ui=test
```

If you wish to check that all test cases in `fixtures.json` were used set the `--ui-check-missing` flag. Of course this is meaningful only if you run the tests on the whole `device_tests` folder.

```sh
pytest tests/device_tests --ui=test --ui-check-missing
```

You can also skip tests marked as `skip_ui`.

```sh
pytest tests/device_tests --ui=test -m "not skip_ui"
```

# Updating Fixtures ("Recording")

Short version:
```sh
poetry run make -C core test_emu_ui_record
```

Long version:

The `--ui` pytest argument has two options:

- **record**: Create screenshots and calculate theirs hash for each test.
The screenshots are gitignored, but the hash is included in git.
- **test**: Create screenshots, calculate theirs hash and test the hash against
the one stored in git.

If you want to make a change in the UI you simply run `--ui=record`. An easy way
to proceed is to run `--ui=test` at first, see what tests fail (see the Reports section below),
decide if those changes are the ones you expected and then finally run the `--ui=record`
and commit the new hashes.

Also here we provide an option to check the `fixtures.json` file. Use `--ui-check-missing` flag again to make sure there are no extra fixtures in the file:

```sh
pytest tests/device_tests --ui=record --ui-check-missing
```

## Reports

### Tests

Each `--ui=test` creates a clear report which tests passed and which failed.
The index file is stored in `tests/ui_tests/reporting/reports/test/index.html`.
The script `tests/show_results.py` starts a local HTTP server that serves this page --
this is necessary for access to browser local storage, which enables a simple reviewer
UI.

On CI this report is published as an artifact. You can see the latest master report [here](https://gitlab.com/satoshilabs/trezor/trezor-firmware/-/jobs/artifacts/master/file/test_ui_report/index.html?job=core%20device%20ui%20test). The reviewer features work directly here.

If needed, you can use `python3 -m tests.ui_tests` to regenerate the report from local
recorded screens.

### Master diff

In the ui tests folder you will also find a Python script `report_master_diff.py`, which
creates a report where you find which tests were altered, added, or removed relative to
master. This useful for Pull Requests.

This report is available as an artifact on CI as well. You can find it by
visiting the "core unix ui changes" job in your pipeline - browse the
artifacts and open `master_diff/index.html`.
