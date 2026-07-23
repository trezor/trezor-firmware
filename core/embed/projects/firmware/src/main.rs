#![no_std]
#![no_main]

// force pull in Rust generated symbols (incl. the panic handler)
// rustc drops unused deps, so this is required for `api`'s
// `#[global_allocator]`.
#[cfg(feature = "app_loading")]
use api as _;
use sys as _;
use trezor_lib as _;
