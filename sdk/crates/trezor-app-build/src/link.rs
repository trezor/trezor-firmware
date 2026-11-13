use crate::helpers::{is_linux, is_macos, is_unit_test};
use anyhow::Result;

pub fn link() -> Result<()> {
    if !is_unit_test() {
        if is_macos() {
            // On macOS, link to System framework to get memcpy, memset, etc.
            println!("cargo:rustc-link-lib=System");
            println!("cargo:rustc-link-arg=-Wl,-export_dynamic");
        } else if is_linux() {
            // On Linux, link to C library to get __libc_start_main, memcpy, etc.
            println!("cargo:rustc-link-lib=c");
            println!("cargo:rustc-link-arg=-shared");
        }
    }
    Ok(())
}
