# python-trezor

[![image](https://travis-ci.org/trezor/python-trezor.svg?branch=master)](https://travis-ci.org/trezor/python-trezor) [![repology](https://repology.org/badge/tiny-repos/python:trezor.svg)](https://repology.org/metapackage/python:trezor) [![image](https://badges.gitter.im/trezor/community.svg)](https://gitter.im/trezor/community)

Python library and commandline client for communicating with Trezor
Hardware Wallet

See <https://trezor.io> for more information

## Install

Python-trezor requires Python 3.5 or higher, and libusb 1.0. The easiest
way to install it is with `pip`. The rest of this guide assumes you have
a working `pip`; if not, you can refer to [this
guide](https://packaging.python.org/tutorials/installing-packages/).

### Quick installation

On a typical Linux / Mac / BSD system, you already have all you need.
Install `trezor` with:

```sh
pip3 install --upgrade setuptools
pip3 install trezor
```

On Windows, you also need to install
[libusb](https://github.com/libusb/libusb/wiki/Windows) and the
appropriate [drivers](https://zadig.akeo.ie/). This is, unfortunately, a
topic bigger than this README.

### Older Trezor One support

If your Trezor One is on firmware **1.6.3** or older, you will need to install
and use the Trezor Bridge.

#### Debian / Ubuntu

On a Debian or Ubuntu based system, you can install these:

```sh
sudo apt-get install python3-dev python3-pip cython3 libusb-1.0-0-dev libudev-dev
```

#### Windows

On a Windows based system, you can install these (for more info on choco, refer to [this](https://chocolatey.org/install)):

```sh
choco install vcbuildtools python3 protoc
refreshenv
pip3 install protobuf
```

### Ethereum support

Ethereum requires additional python packages. Instead of
`pip3 install trezor`, specify `pip3 install trezor[ethereum]`.

### FreeBSD

On FreeBSD you can install the packages:

```sh
pkg install security/py-trezor
```

or build via ports:

```sh
cd /usr/ports/security/py-trezor
make install clean
```

### Building from source

Sometimes you might need to install the latest-and-greatest unreleased version
straight from GitHub. You will need some prerequisites first:

```sh
sudo apt-get install protobuf-compiler protobuf-dev
pip3 install protobuf
```

If you just need to install the package, you can use pip again:
```sh
pip3 install git+https://github.com/trezor/python-trezor
```

If you want to work on the sources, make a local clone:

```sh
git clone https://github.com/trezor/python-trezor
cd python-trezor
python3 setup.py prebuild
python3 setup.py develop
```

## Command line client (trezorctl)

The included `trezorctl` python script can perform various tasks such as
changing setting in the Trezor, signing transactions, retrieving account
info and addresses. See the [docs/](docs/) sub folder for detailed
examples and options.

NOTE: An older version of the `trezorctl` command is [available for
Debian Stretch](https://packages.debian.org/en/stretch/python-trezor)
(and comes pre-installed on [Tails OS](https://tails.boum.org/)).

## Python Library

You can use this python library to interact with a Bitcoin Trezor and
use its capabilities in your application. See examples here in the
[tools/](tools/) sub folder.

## PIN Entering

When you are asked for PIN, you have to enter scrambled PIN. Follow the
numbers shown on Trezor display and enter the their positions using the
numeric keyboard mapping:

|   |   |   |
|---|---|---|
| 7 | 8 | 9 |
| 4 | 5 | 6 |
| 1 | 2 | 3 |

Example: your PIN is **1234** and Trezor is displaying the following:

|   |   |   |
|---|---|---|
| 2 | 8 | 3 |
| 5 | 4 | 6 |
| 7 | 9 | 1 |

You have to enter: **3795**

## Contributing

Python-trezor pulls coins info and protobuf messages from
[trezor-common](https://github.com/trezor/trezor-common) repository. If
you are developing new features for Trezor, you will want to start
there. Once your changes are accepted to `trezor-common`, you can make a
PR against this repository. Don't forget to update the submodule with:

```sh
git submodule update --init --remote
```

Then, rebuild the protobuf messages and get `coins.json` by running:

```sh
python3 setup.py prebuild
```

To get support for BTC-like coins, these steps are enough and no further
changes to the library are necessary.
