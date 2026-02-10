//! Bridge between the `rust-miniscript` crate and MicroPython.
//!
//! Exposes a single function `compile_descriptor` that takes a Bitcoin output
//! descriptor string (with concrete public keys) and returns the explicit
//! witness script bytes.

extern crate alloc;

use miniscript::{Descriptor, bitcoin};

use crate::error::Error;
use crate::micropython::buffer::StrBuffer;
use crate::micropython::macros::{obj_fn_1, obj_module};
use crate::micropython::{module::Module, obj::Obj, qstr::Qstr, util};
use core::str::FromStr;

// ---------------------------------------------------------------------------
// Global allocator (needed by `alloc` / `miniscript` in no_std)
// ---------------------------------------------------------------------------

use static_alloc::Bump;

// 8KB bump allocator for descriptor compilation
#[global_allocator]
static ALLOCATOR: Bump<[u8; 8192]> = Bump::uninit();

fn parse(desc_str: &str) -> Result<Descriptor<bitcoin::PublicKey>, miniscript::Error> {
    Descriptor::<bitcoin::PublicKey>::from_str(desc_str)
}

pub extern "C" fn upy_compile_descriptor(descriptor: Obj) -> Obj {
    let block = || {
        // Read the MicroPython string.
        let desc_str: StrBuffer = descriptor.try_into()?;

        let desc = parse(&desc_str)
            .map_err(|_| Error::ValueError(c"Invalid descriptor"))?;

        desc.explicit_script().map_err(|_| Error::ValueError(c"No script"))?.as_bytes().try_into()
    };
    unsafe { util::try_or_raise(block) }
}

// ---------------------------------------------------------------------------
// Module definition
// ---------------------------------------------------------------------------

#[no_mangle]
pub static mp_module_trezorminiscript: Module = obj_module! {
    /// def compile(descriptor: str) -> bytes:
    ///     """Parse a Bitcoin output descriptor (with concrete public keys)
    ///     and return the witness script bytes."""
    Qstr::MP_QSTR_compile => obj_fn_1!(upy_compile_descriptor).as_obj(),

    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezorminiscript.to_obj()
};
