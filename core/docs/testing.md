# Testing

## Testing with python-trezor

Apart from the internal tests, Trezor core has a suite of integration tests in the [`python-trezor`](https://github.com/trezor/python-trezor) library. There are several ways to use that.

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

You will need a separate checkout of `python-trezor`. It's probably a good idea to do this outside the `trezor-core` directory:

```sh
git clone https://github.com/trezor/python-trezor
```

Prepare a virtual environment with all the requirements, and switch into it. Again, it's easiest to do this with `pipenv`:

```sh
cd python-trezor
pipenv install -r requirements-dev.txt
pipenv install -e .
pipenv shell
```

Alternately, if you have an existing virtualenv, you can install python-trezor in "develop" mode:

```sh
python setup.py develop
```

If you want to test against the emulator, run it in a separate terminal from the `trezor-core` checkout directory:

```sh
PYOPT=0 ./emu.sh
```

Find the device address and export it as an environment variable. For the emulator, this is:

```sh
export TREZOR_PATH="udp:127.0.0.1:21324"
```

(You can find other devices with `trezorctl list`.)

Now you can run the test suite, either from `python-trezor` or `trezor-core` root directory:

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

### 3. Submitting tests for new features

When you're happy with your tests, follow these steps:

1. Mark each of your tests with the name of your feature. E.g., `@pytest.mark.ultracoin2000`.
2. Also mark each of your tests with `@pytest.mark.xfail`. That means that the test is expected to fail.
   If you want to run that test as usual, run `pytest --runxfail`
3. Submit a PR to `python-trezor`, containing these tests.
4. Edit the file `trezor-core/pytest.ini`, and add your marker to the `run_xfail` item:

   ``` ini
   run_xfail = lisk nem ultracoin2000
   ```

   This will cause your PR to re-enable the `xfail`ed tests. That way we will see whether your feature actually implements what it claims.

5. Submit a PR to `trezor-core`.
6. Optionally, if you like to be extra nice: after both your PRs are accepted, submit a new one to `python-trezor` that removes the `xfail` markers, and one to `trezor-core` that removes the `run_xfail` entry.
