# trezor-thp

Rust library for *Trezor Host Protocol*. THP facilitates communication between an application
on a host computer and a [Trezor] cryptocurrency wallet.

To learn more about THP, please see the [full specification][THP-spec].

## Design

The goal of the library is to be used by both bare-metal firmware and desktop applications.

- Implements both the Host and the Device (Trezor) side.
- Usable on `no_std` and without `core::alloc`.
- I/O-free to make integration into any kind of event loop possible.
- Usable with any protobuf and cryptography libraries.
- Minimal dependencies.

Due to these requirements, the crate is very low-level - it provides a library of components that
you need to assemble to get a high-level abstraction of THP sessions.

Crates that provide a higher-level interface:
- [trezor-client](https://crates.io/crates/trezor-client) (work in progress)

## Examples

The examples assume Trezor emulator available through UDP.

```console
cargo run --example ping-emulator
cargo run --example host-cli
```

## Features

None yet.

## Other implementations

- [trezorlib](https://github.com/trezor/trezor-firmware/tree/main/python/src/trezorlib/)
- [Suite/Connect](https://github.com/trezor/trezor-suite/tree/develop/packages/protocol/src/protocol-thp/)

## Credits

- [Trezor](https://github.com/trezor/trezor-firmware)

[THP-spec]: https://docs.trezor.io/trezor-firmware/common/thp/specification.html
[Trezor]: https://trezor.io/
