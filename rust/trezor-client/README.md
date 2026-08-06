# trezor-client

[![Downloads][downloads-badge]][crates-io]

A fork of a [fork](https://github.com/romanz/rust-trezor-api) of a [library](https://github.com/stevenroose/rust-trezor-api) that provides a way to communicate with Trezor devices from a Rust project.

Previous iterations provided implementations for Bitcoin only.
This crate also provides an Ethereum interface, mainly for use in [alloy-rs](https://github.com/alloy-rs/alloy).

## Requirements

**MSRV: 1.60**

See the [Trezor guide](https://trezor.io/learn/a/os-requirements-for-trezor) on how to install and use the Trezor Suite app.

Last tested with firmware v2.4.2.

## Examples / Tests

`cargo run --example features`

## Features

-   `bitcoin` and `ethereum`: client implementation and full support;
-   `cardano`, `monero`, `nem`, `ripple`, `stellar`, `tezos` and `tron`: only protobuf bindings.

## Credits

See the `AUTHORS` file.

[downloads-badge]: https://img.shields.io/crates/d/trezor-client?style=for-the-badge&logo=rust
[crates-io]: https://crates.io/crates/trezor-client
