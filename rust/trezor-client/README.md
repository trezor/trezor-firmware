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
-   `cardano`, `lisk`, `monero`, `nem`, `ontology`, `ripple`, `stellar`, `tezos`, and`tron`: only protobuf bindings.

## Future

At the moment, not looking into expanding more than what's necessary to maintain compatability/usability with ethers-rs.

## Credits

-   [Trezor](https://github.com/trezor/trezor-firmware)
-   [stevenroose](https://github.com/stevenroose)
-   [romanz](https://github.com/romanz)

[downloads-badge]: https://img.shields.io/crates/d/trezor-client?style=for-the-badge&logo=rust
[crates-io]: https://crates.io/crates/trezor-client
[license-badge]: https://img.shields.io/badge/license-CC0--1.0-blue.svg?style=for-the-badge
[license-url]: https://github.com/joshieDo/rust-trezor-api/blob/master/LICENSE
[actions-badge]: https://img.shields.io/github/actions/workflow/status/joshieDo/rust-trezor-api/ci.yml?branch=master&style=for-the-badge
[actions-url]: https://github.com/joshieDo/rust-trezor-api/actions?query=workflow%3ACI+branch%3Amaster
