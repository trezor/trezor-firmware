# Testing

## Testing with python-trezor

Apart from the internal tests, Trezor core has a suite of integration tests in the
`python` subdirectory. There are several ways to use that.


### 1. Running the full test suite

[pipenv] is a tool for making reproducible Python environments. Install it with:
```sh
sudo pip3 install pipenv
```
In the `trezor-firmware` checkout, install the environment:
```sh
pipenv sync
```
And run the automated tests:
```sh
pipenv run make -C core test_emu
```


### 2. Running tests manually

Install the pipenv environment as outlined above. Then switch to a shell inside the
environment:

```sh
pipenv shell
```

If you want to test against the emulator, run it in a separate terminal from the `core`
subdirectory:
```sh
PYOPT=0 ./emu.sh
```

Find the device address and export it as an environment variable. For the emulator, this
is:
```sh
export TREZOR_PATH="udp:127.0.0.1:21324"
```
(You can find other devices with `trezorctl list`.)

Now you can run the test suite with `pytest`, either from `python` or `core` directory:
```sh
pytest
```

Or from anywhere else:
```sh
pytest --pyargs trezorlib.tests.device_tests  # this works from other locations
```

You can place your own tests in [device_tests] directory. See test style guide (TODO).

If you only want to run a particular test, pick it with `-k <keyword>` or `-m <marker>`:

```sh
pytest -k nem      # only runs tests that have "nem" in the name
pytest -m stellar  # only runs tests marked with @pytest.mark.stellar
```

If you want to see debugging information and protocol dumps, run with `-v`.


### 3. Using markers

When you're developing a new currency, you should mark all tests that belong to that
currency. For example, if your currency is called NewCoin, your device tests should have
the following marker:

```python
@pytest.mark.newcoin
```

This marker must be registered in [REGISTERED_MARKERS] file.

If you wish to run a test only on TT, mark it with `@pytest.mark.skip_t1`.
If the test should only run on T1, mark it with `@pytest.mark.skip_t2`.
You must not use both on the same test.

[pipenv]: https://docs.pipenv.org/
[device_tests]: ../../python/trezorlib/tests/device_tests
[REGISTERED_MARKERS]: ../../python/trezorlib/tests/device_tests/REGISTERED_MARKERS


## Extended testing and debugging

### Building for debugging (Emulator only)

Build the debuggable unix binary so you can attach the gdb or lldb.
This removes optimizations and reduces address space randomizaiton.

```sh
make build_unix_debug
```

The final executable is significantly slower due to ASAN(Address Sanitizer) integration.
If you wan't to catch some memory errors use this.

```sh
time ASAN_OPTIONS=verbosity=1:detect_invalid_pointer_pairs=1:strict_init_order=true:strict_string_checks=true TREZOR_PROFILE="" pipenv run make test_emu
```

### Coverage (Emulator only)

Get the Python code coverage report.

If you want to get HTML/console summary output you need to install the __coverage.py__ tool.

```sh
pip3 install coverage
```

First you need to enable the __settrace__ featurine in the __./embed/unix/mpconfigport.h__:

```c
#define MICROPY_PY_SYS_TRACE (1)
```

Rebuild the emulator and run the tests with coverage output.

```sh
make build_unix && make coverage
```
