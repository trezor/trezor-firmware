#![no_std]
#![no_main]

use trezor_lib as _;

// rustc drops unused deps, so this is required for `api`'s `#[global_allocator]`.
#[cfg(feature = "app_loading")]
use api as _;
