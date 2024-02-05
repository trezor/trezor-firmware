# Testing

We have two types of tests in Core:

1. Unit tests that are specific to Trezor Core.
2. Common tests, which are common to both Trezor Core (Model T, Safe 3) and Legacy (Model one). Device tests belong to this category.

## Core unit tests

Unit tests are placed in the `core/tests/` directory.

To start them, [build unix port](../build/emulator.md) and run the following command from `core/`:

```sh
make test                                           # run all unit test
make test TESTOPTS=test_apps.bitcoin.address.py     # run a specific test
```

## Common tests

See the [tests](../../tests/index.md) section.
