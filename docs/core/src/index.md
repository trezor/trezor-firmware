# Trezor Core

Trezor Core uses [MicroPython](https://github.com/micropython/micropython), it is a Python implementation for embedded systems, which allows us to have an application layer in Python, which makes the code significantly more readable and sustainable. This is what you find in the `src` folder.

Not everything is in Python though, we need to use C occasionally, usually for performance reasons. That is what `embed/extmod` is for. It extends MicroPython's modules with a number of our owns and serves as a bridge between C and Python codebase. Related to that, `mocks` contain Python mocks of those functions to improve readability and IDE functioning.

## Boot

Module `src/main.py` is the first one to be invoked in MicroPython. It starts the USB, initializes the wire codec and boots applications (see [Apps](apps.md)).
