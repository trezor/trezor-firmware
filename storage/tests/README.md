# Trezor Storage tests

This repository contains all the necessary files to properly test Trezor's internal storage.

This repository consists of:

- `c`: The actual C version is implemented in the main `storage` folder, however we need some other accompanying files to build it on computer.
- `c0`: This is the older version of Trezor storage. It is used to test upgrades from the older format to the newer one.
- `python`: Python version. Serves as a reference implementation and is implemented purely for the goal of properly testing the C version.
- `tests`: Most of the tests run the two implementations against each other. Uses Pytest and [hypothesis](https://hypothesis.works) for random tests.
