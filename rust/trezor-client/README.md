# trezor-client

[![Downloads][downloads-badge]][crates-io]
[![License][license-badge]][license-url]
[![CI Status][actions-badge]][actions-url]

A fork of a [fork](https://github.com/romanz/rust-trezor-api) of a [library](https://github.com/stevenroose/rust-trezor-api) that provides a way to communicate with a Trezor T device from a Rust project.

Previous iterations provided implementations for Bitcoin only. **This crate also provides an Ethereum interface**, mainly for use in [ethers-rs](https://github.com/gakonst/ethers-rs/).

## Requirements

**MSRV: 1.60**

See the [Trezor guide](https://trezor.io/learn/a/os-requirements-for-trezor) on how to install and use the Trezor Suite app.

Last tested with firmware v2.4.2.

## Examples / Tests

`cargo run --example features`

## Features

-   `bitcoin` and `ethereum`: client implementation and full support;
-   `cardano`, `monero`, `nem`, `ripple`, `stellar` and `tezos`: only protobuf bindings.

## Credits

-   [Trezor](https://github.com/trezor/trezor-firmware)
-   [joshieDo](https://github.com/joshieDo)
-   [Piyush Kumar](https://github.com/wszdexdrf)
-   [stevenroose](https://github.com/stevenroose)
-   [romanz](https://github.com/romanz)
-   [DaniPopes](https://github.com/DaniPopes)

[downloads-badge]: https://img.shields.io/crates/d/trezor-client?style=for-the-badge&logo=rust
[crates-io]: https://crates.io/crates/trezor-client
[license-badge]: https://img.shields.io/badge/license-CC0--1.0-blue.svg?style=for-the-badge
[license-url]: https://github.com/trezor/trezor-firmware/blob/master/rust/trezor-client/LICENSE
