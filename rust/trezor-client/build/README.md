# trezor-client-build

Simple build script for [`trezor-client`](../).
Builds the Rust bindings for the [Trezor protobufs](../../../common/protob/).

This crate is separate from the main crate to avoid dependencies on the
protobuf compiler (`protoc`) and the `protobuf-codegen` crate in `trezor-client`.
