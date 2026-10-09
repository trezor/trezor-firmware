#![no_std]
#![no_main]

// TEMPORARY: app loading registers `api`'s `#[global_allocator]` (the app
// heap) and miniscript registers `trezor_lib`'s (MicroPython's tracked
// allocator), and a binary can have only one. Keep the two features mutually
// exclusive until the allocators can coexist.
#[cfg(all(feature = "app_loading", feature = "miniscript"))]
compile_error!("features `app_loading` and `miniscript` cannot be enabled together");

// rustc drops unused deps, so this is required for `api`'s
// `#[global_allocator]`.
#[cfg(feature = "app_loading")]
use api as _;
use sys as _;
use trezor_lib as _;
