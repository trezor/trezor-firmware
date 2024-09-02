# Running device tests

## 1. Running the full test suite

_Note: You need Poetry, as mentioned in the core's [documentation](https://docs.trezor.io/trezor-firmware/core/) section._

In the `trezor-firmware` checkout, in the root of the monorepo, install the environment:

```sh
poetry install
```

And run the automated tests:

```sh
poetry run make -C core test_emu
```

## 2. Running tests manually

Install the poetry environment as outlined above. Then switch to a shell inside the
environment:

```sh
poetry shell
```

If you want to test against the emulator, run it in a separate terminal:
```sh
./core/emu.py
```

Now you can run the test suite with `pytest` from the root directory:
```sh
pytest tests/device_tests
```

### Useful Tips

The tests are randomized using the [pytest-random-order] plugin. The random seed is printed in the header of the tests output, in case you need to run the tests in the same order.

If you only want to run a particular test, pick it with `-k <keyword>` or `-m <marker>`:

```sh
pytest -k nem      # only runs tests that have "nem" in the name
pytest -k "nem or stellar"  # only runs tests that have "nem" or "stellar" in the name
pytest -m stellar  # only runs tests marked with @pytest.mark.stellar
```

If you want to see debugging information and protocol dumps, run with `-v`.

Print statements from testing files are not shown by default. To enable them, use `-s` flag.

If you would like to interact with the device (i.e. press the buttons yourself), just prefix pytest with `INTERACT=1`:

```sh
INTERACT=1 pytest tests/device_tests
```

When testing transaction signing, there is an option to check transaction hashes on-chain using Blockbook. It is chosen by setting `CHECK_ON_CHAIN=1` environment variable before running the tests.

```sh
CHECK_ON_CHAIN=1 pytest tests/device_tests
```

To run the tests quicker, spawn the emulator with disabled animations using `-a` flag.

```sh
./core/emu.py -a
```

To run the tests even quicker, the emulator should come from a frozen build. (However, then changes to python code files are not reflected in emulator, one needs to build it again each time.)

```sh
PYOPT=0 make build_unix_frozen
```

It is possible to specify the timeout for each test in seconds, using `PYTEST_TIMEOUT` env variable.
```sh
PYTEST_TIMEOUT=15 pytest tests/device_tests
```

When running tests from Makefile target, it is possible to specify `TESTOPTS` env variable with testing options, as if pytest would be called normally.

```sh
TESTOPTS="-x -v -k test_msg_backup_device.py" make test_emu
```

When troubleshooting an unstable test that is failing occasionally, following runs it until it fails (so failure is visible on screen):

```sh
export TESTOPTS="-x -v -k test_msg_backup_device.py"
while make test_emu; do sleep 1; done
```

## 3. Using markers

When you're developing a new currency, you should mark all tests that belong to that
currency. For example, if your currency is called NewCoin, your device tests should have
the following marker:

```python
@pytest.mark.newcoin
```

This marker must be registered in `REGISTERED_MARKERS` file in `tests` folder.

Tests can be run only for specific models. The marker `@pytest.mark.models()` can be
used to narrow the selection:

* `@pytest.mark.models("t3b1", "t2t1)` - only for Safe 3 rev2 and Trezor T
* `@pytest.mark.models("core")` - only for trezor-core models (skip Trezor One)
* `@pytest.mark.models(skip="t3t1")` - for all models except Safe 5
* `@pytest.mark.models("core", skip="t3t1")` - for all trezor-core models except Safe 5

Arguments can be a list of internal model names, or one of the following shortcuts:

* `core` - all trezor-core models
* `legacy` - just Trezor One
* `safe` - Trezor Safe family
* `safe3` - Trezor Safe 3 (covers T2B1 and T2T1)
* `mercury` - covers the `mercury` layout (currently T3T1 only)

You can specify a list as positional arguments, and exclude from it via `skip` keyword argument.

You can provide a list of strings, a list of `TrezorModel` instances, or a
comma-separated string of model names or shortcuts.

You can specify a skip reason as `reason="TODO implement for Mercury too"`.

[pytest-random-order]: https://pypi.org/project/pytest-random-order/

## Extended testing and debugging

### Building for debugging (Emulator only)

Build the debuggable unix binary so you can attach the gdb or lldb.
This removes optimizations and reduces address space randomizaiton.

```sh
make build_unix_debug
```

The final executable is significantly slower due to ASAN(Address Sanitizer) integration.
If you want to catch some memory errors use this.

```sh
time ASAN_OPTIONS=verbosity=1:detect_invalid_pointer_pairs=1:strict_init_order=true:strict_string_checks=true TREZOR_PROFILE="" poetry run make test_emu
```

### Coverage (Emulator only)

Get the Python code coverage report.

If you want to get HTML/console summary output you need to install the __coverage.py__ tool.

```sh
pip3 install coverage
```

Run the tests with coverage output.

```sh
make build_unix && make coverage
```
