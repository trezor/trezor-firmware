# trezorlib

[![repology](https://repology.org/badge/tiny-repos/python:trezor.svg)](https://repology.org/metapackage/python:trezor) [![image](https://badges.gitter.im/trezor/community.svg)](https://gitter.im/trezor/community)

Python library and command-line client for communicating with Trezor
Hardware Wallet.

See <https://trezor.io> for more information.

## Install

Python Trezor tools require Python 3.9 or higher, and libusb 1.0. The easiest
way to install it is with `pip`. The rest of this guide assumes you have
a working `pip`; if not, you can refer to [this
guide](https://packaging.python.org/tutorials/installing-packages/).

On a typical system, you already have all you need. Install `trezor` with:

```sh
pip3 install trezor
```

On Windows, you also need to either install [Trezor Bridge](https://suite.trezor.io/web/bridge/), or
[libusb](https://github.com/libusb/libusb/wiki/Windows) and the appropriate
[drivers](https://zadig.akeo.ie/).

### Firmware version requirements

Current trezorlib version supports Trezor One version 1.8.0 and up, Trezor T version
2.1.0 and up, and all versions of the Trezor Safe family.

For firmware versions below 1.8.0 and 2.1.0 respectively, the only supported operation
is "upgrade firmware".

Trezor One with firmware _older than 1.7.0_ and bootloader _older than 1.6.0_
(including pre-2021 fresh-out-of-the-box units) will not be recognized, unless
you install HIDAPI support (see below).

### Installation options

* **Ethereum**: To support Ethereum signing from command line, additional packages are
  needed. Install with:

  ```sh
  pip3 install trezor[ethereum]
  ```

* **Stellar**: To support Stellar signing from command line, additional packages are
  needed. Install with:

  ```sh
  pip3 install trezor[stellar]
  ```

* **Firmware-less Trezor One**: If you are setting up a brand new Trezor One
  manufactured before 2021 (with pre-installed bootloader older than 1.6.0), you will
  need HIDAPI support. On Linux, you will need the following packages (or their
  equivalents) as prerequisites: `python3-dev`, `cython3`, `libusb-1.0-0-dev`,
  `libudev-dev`.

  Install with:

  ```sh
  pip3 install trezor[hidapi]
  ```

To install all four, use `pip3 install trezor[hidapi,ethereum,stellar]`.

### Distro packages

Check out [Repology](https://repology.org/metapackage/python:trezor) to see if your
operating system has an up-to-date python-trezor package.

### Running from source

Install the [uv](https://docs.astral.sh/uv/) tool, checkout `trezor-firmware` from git,
and activate the uv environment:

```sh
git clone https://github.com/trezor/trezor-firmware
cd trezor-firmware
git submodule update --init --recursive
uv sync
source .venv/bin/activate
```

In this environment, trezorlib and the `trezorctl` tool is running from the live
sources, so your changes are immediately effective.

## Command line client (trezorctl)

The included `trezorctl` python script can perform various tasks such as
changing setting in the Trezor, signing transactions, retrieving account
info and addresses. See the
[python/docs/](https://github.com/trezor/trezor-firmware/tree/main/python/docs)
sub folder for detailed examples and options.

NOTE: An older version of the `trezorctl` command is [available for
Debian Stretch](https://packages.debian.org/en/stretch/python-trezor)
(and comes pre-installed on [Tails OS](https://tails.boum.org/)).

## Python Library

You can use this python library to interact with a Trezor and use its capabilities in
your application. See examples here in the
[tools/](https://github.com/trezor/trezor-firmware/tree/main/python/tools)
sub folder.

## Changelog

Visit [CHANGELOG.md] for the latest changes.

[CHANGELOG.md]: https://github.com/trezor/trezor-firmware/blob/main/python/CHANGELOG.md

## Contributing

If you want to change protobuf definitions, you will need to regenerate definitions in
the `python/` subdirectory.

First, make sure your submodules are up-to-date with:

```sh
git submodule update --init --recursive
```

Then, rebuild the protobuf messages by running, from the `trezor-firmware` top-level
directory:

```sh
make gen
```
