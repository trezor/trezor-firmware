#![no_std]
#![no_main]

// force pull in Rust generated symbols (incl. the panic handler)
use io as _;
use sys as _;
use trezor_lib as _;
