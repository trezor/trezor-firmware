// SPDX-License-Identifier: CC0-1.0

// Trezor fork: do not build the bundled libsecp256k1. The firmware links
// against the vendored copy at vendor/secp256k1-zkp/, compiled by SCons,
// which exports the canonical (unprefixed) secp256k1_* symbols.
//
// Emitting rust_secp_no_symbol_renaming makes the FFI #[link_name]
// attributes use those unprefixed names.

#![deny(non_upper_case_globals)]
#![deny(non_camel_case_types)]
#![deny(non_snake_case)]
#![deny(unused_mut)]

fn main() {
    println!("cargo:rustc-cfg=rust_secp_no_symbol_renaming");
    println!("cargo:rerun-if-changed=build.rs");
}
