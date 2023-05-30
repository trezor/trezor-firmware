# eulith-trezorlib

Python library and command-line client for communicating with Trezor
Hardware Wallet, modified to work more closely with Eulith clients & applications.

See <https://trezor.io> and <https://eulith.com> for more information.

## !! This is a derivative package of Trezor !!
For the original package, please see https://github.com/trezor/trezor-firmware

This package has been modified primarily to sort out dependency issues that come up when
trying to use the original trezor package with Ethereum tooling like `web3py`.

## Install

Python Trezor tools require Python 3.6 or higher, and libusb 1.0. The easiest
way to install it is with `pip`. The rest of this guide assumes you have
a working `pip`; if not, you can refer to [this
guide](https://packaging.python.org/tutorials/installing-packages/).

On a typical system, you already have all you need. Install `trezor` with:

```sh
pip3 install eulith-trezor
```

On Windows, you also need to either install [Trezor Bridge](https://suite.trezor.io/web/bridge/), or
[libusb](https://github.com/libusb/libusb/wiki/Windows) and the appropriate
[drivers](https://zadig.akeo.ie/).

### Firmware version requirements

Current trezorlib version supports Trezor One version 1.8.0 and up, and Trezor T version
2.1.0 and up.

For firmware versions below 1.8.0 and 2.1.0 respectively, the only supported operation
is "upgrade firmware".

Trezor One with firmware _older than 1.7.0_ and bootloader _older than 1.6.0_
(including pre-2021 fresh-out-of-the-box units) will not be recognized, unless
you install HIDAPI support (see below).
