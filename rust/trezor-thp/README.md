# trezor-thp

Rust library for *Trezor Host Protocol*. THP facilitates communication between an application
on host computer and a [Trezor] cryptocurrency wallet.

To learn more about THP please see the [full specification][THP-spec].

## Design

The goal of the library is to be used both by bare metal firmware as well as desktop applications.

- Implements both Host and Device (Trezor) side.
- Usable on `no_std` and without `core::alloc`.
- I/O-free to make integration into any kind of event loop possible.
- Usable with any protobuf and cryptography libraries.
- Minimal dependencies.

Due to these requirements the crate is very low-level - it provides a library of components that
you need to assemble to get a high-level abstraction of THP sessions.

Crates that provide higher level interface:
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

- trezorlib
- suite

## Credits

- [Trezor](https://github.com/trezor/trezor-firmware)

[THP-spec]: https://docs.trezor.io/trezor-firmware/common/thp/specification.html
[Trezor]: https://trezor.io/
