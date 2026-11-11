# Running device tests

## 1. Running the full test suite

_Note: You need Uv, as mentioned in the core's [documentation](https://docs.trezor.io/trezor-firmware/core/) section._

In the `trezor-firmware` checkout, in the root of the monorepo, install the environment:

```sh
uv sync
```

And run the automated tests:

```sh
uv run make -C core test_emu
```

## 2. Running tests manually

Install the `uv` environment as outlined above. Then activate the environment:

```sh
source .venv/bin/activate
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

To watch WARD confirmations, verified labels, and warnings in the emulator GUI,
omit `-h` and add `--ward-ui-delay=2` to pause for two seconds before each automated
input in `test_ward*.py` and `test_display_address.py`. Confirmations remain automatic;
do not click the emulator while the tests run. The default delay is zero.

```sh
export WARDD_SUITE_DIR=/path/to/trezor-suite  # checkout containing packages/wardd
./core/emu.py -t -P 31720 -q -c python -m pytest \
    tests/device_tests/misc/test_ward_relay.py \
    tests/device_tests/misc/test_display_address.py \
    tests/device_tests/misc/test_ward.py --ward-ui-delay=2 -v
```

The relay tests also need the Suite checkout's wardd dependencies installed.

### WARD hardware channels

The Hardware tests workflow includes dedicated WARD jobs for T3T1 and T3W1.
Each job builds one service-enabled image and tests both routes: wallet fallback
with the service unbound, then the bound USB service channel. Separate results
also cover wardd connecting directly to USB. The service tests reject proof and
node responses sent through the wallet channel, and check fallback after service
disconnect and recovery after reconnect. Both mock and HTTP WARD managers run.

These jobs retain DebugLink for automated confirmations and use SWO instead of
the VCP console to stay within the USB endpoint budget. Regular hardware jobs
retain VCP. The workflow checks out a pinned matching Suite revision and installs
wardd dependencies automatically.

To start both models from the branch being tested:

```sh
gh workflow run core-hw.yml --ref petrsusil/ward-service-channel \
    -f 'models_json=["T3T1","T3W1"]' -f ward_only=true
```

`ward_only=true` skips the regular device, legacy, and Monero jobs. Native
transport probes first test repeated binding/release, idle timeouts, and wallet
traffic while the service is bound, without a daemon backend or WARD manager.
Their phase logs and the native daemon's complete output are uploaded with the
channel results. The native end-to-end tests report whether sync, write, lookup,
or shutdown was in progress when a failure occurred.

The jobs then run `tools/ward_stack.py`'s single-device modes on the device
(`tests/device_tests/misc/test_ward_e2e.py`): the default write and lookup and
`--long`, each over the wallet relay and the service channel against an HTTP WARD
manager. `--extra_long` takes hours on hardware and is left to the stack. Last,
`tools/ward_adversarial.py --hardware` runs all attack/rejection groups: the
firmware, manager and crypto tests and the offline cache on the device, and the
wardd, history and adapter suites on the runner. The image includes the offline
store (`--ward`) for the cache tests. Multi-device races and recovery need
several devices and are not run.

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
xtask build firmware -e --pyopt=false --frozen
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
* `delizia` - covers the `delizia` UI (currently T3T1 only)
* `eckhart` - covers the `eckhart` UI (currently T3W1 only)

You can specify a list as positional arguments, and exclude from it via `skip` keyword argument.

You can provide a list of strings, a list of `TrezorModel` instances, or a
comma-separated string of model names or shortcuts.

You can specify a skip reason as `reason="TODO implement for Delizia too"`.

[pytest-random-order]: https://pypi.org/project/pytest-random-order/

## 4. Extended testing and debugging

### Building for debugging (Emulator only)

Build the debuggable unix binary so you can attach the gdb or lldb.
This removes optimizations and reduces address space randomizaiton.

```sh
make build_unix_debug
```

The final executable is significantly slower due to ASAN(Address Sanitizer) integration.
If you want to catch some memory errors use this.

```sh
time ASAN_OPTIONS=verbosity=1:detect_invalid_pointer_pairs=1:strict_init_order=true:strict_string_checks=true TREZOR_PROFILE="" uv run make test_emu
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

### GC leak check (both Emulator and Hardware)

DebugLink interface supports polling the device for its current [GC-related information](https://github.com/trezor/trezor-firmware/pull/5091).

On every test setup/teardown, we check for whether the free memory has decreased (indicating that the GC didn't free all allocated heap memory).

By default, the test will fail if a leak is detected. In order to issue a warning instead, use `--warn-on-gc-leak` CLI flag.

## 5. Running tests on hardware over BLE

T3W1 currently cannot do DebugLink over BLE so it must still be connected with USB during testing.

* Build the firmware with secure elements disabled and `--storage-insecure-testing-mode true` to make testing faster.
* In device menu: `Pair & Connect` -> `Forget all`.
* Open your OS Bluetooth settings, forget the Trezor if there, do not connect to it, keep the window open.
* In device menu: `Pair & Connect` -> `Pair new device`.
* Run `trezorctl -vv ble connect` - OS settings should show the pairing code, confirm it there and on device.
* Optionally check the connection: `trezorctl --ble --path "ble:" -vv get-features`.
* Run pytest over BLE: `pytest --ble -v tests/device_tests`, add arguments as required.
