# Testing

## Testing with python-trezor

Apart from the internal tests, Trezor core has a suite of integration tests in the `python` subdirectory. There are several ways to use that.

### 1. Running the suite with pipenv

[`pipenv`](https://docs.pipenv.org/) is a tool for making reproducible Python environments. Install it with:

```sh
sudo pip3 install pipenv
```

Inside `trezor-core` checkout, install the environment:

```sh
pipenv install
```

And run the automated tests:

```sh
pipenv run make test_emu
```

### 2. Developing new tests

Prepare a virtual environment with all the requirements, and switch into it. Again, it's easiest to do this with `pipenv`:

```sh
pipenv install
pipenv shell
```

Alternately, if you have an existing virtualenv, you can install `python` in "develop" mode:

```sh
python setup.py develop
```

If you want to test against the emulator, run it in a separate terminal from the `core` subdirectory:

```sh
PYOPT=0 ./emu.sh
```

Find the device address and export it as an environment variable. For the emulator, this is:

```sh
export TREZOR_PATH="udp:127.0.0.1:21324"
```

(You can find other devices with `trezorctl list`.)

Now you can run the test suite, either from `python` or `core` root directory:

```sh
pytest
```

Or from anywhere else:

```sh
pytest --pyargs trezorlib.tests.device_tests  # this works from other locations
```

You can place your own tests in `trezorlib/tests/device_tests`. See test style guide (TODO).

If you only want to run a particular test, pick it with `-k <keyword>` or `-m <marker>`:

```sh
pytest -k nem      # only runs tests that have "nem" in the name
pytest -m stellar  # only runs tests marked with @pytest.mark.stellar
```

If you want to see debugging information and protocol dumps, run with `-v`.
