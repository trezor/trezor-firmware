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

Now you can run the test suite with:
```sh
pytest
```

You can place your own tests in `trezorlib/tests/device_tests`. See test style guide (TODO).

If you only want to run a particular test, pick it with `-k <keyword>`:
```sh
pytest -k nem   # only runs tests that have "nem" in the name
```
If you have tests marked `xfail` (expected to fail) but you want to run them as usual, run `pytest --runxfail`
If you want to see debugging information and protocol dumps, run with `-v`.
