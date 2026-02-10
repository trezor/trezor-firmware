//! Bridge between the `rust-miniscript` crate and MicroPython.
//!
//! Exposes a single function `compile_descriptor` that takes a Bitcoin output
//! descriptor string (with concrete public keys) and returns the explicit
//! witness script bytes.

extern crate alloc;

use miniscript::{
    bitcoin::secp256k1::Secp256k1,
    descriptor::Wsh,
    expression::{FromTree, Tree},
    Descriptor, DescriptorPublicKey,
};

use crate::{
    error::Error,
    micropython::{
        buffer::StrBuffer,
        macros::{obj_fn_3, obj_module},
        module::Module,
        obj::Obj,
        qstr::Qstr,
        util,
    },
};

#[global_allocator]
static MINISCRIPT_ALLOCATOR: emballoc::Allocator<{ 64 << 10 }> = emballoc::Allocator::new();

fn parse(desc_str: &str) -> Result<Descriptor<DescriptorPublicKey>, miniscript::Error> {
    let tree = Tree::from_str(desc_str)?;
    let top = tree.root();
    let desc = match (top.name(), top.n_children()) {
        ("wsh", 1) => Descriptor::Wsh(Wsh::from_tree(top)?),
        _ => return Err(miniscript::Error::Unexpected(alloc::string::String::new())),
    };
    desc.sanity_check()?; // we don't support insane descriptors
    Ok(desc)
}

pub extern "C" fn upy_compile_descriptor(descriptor: Obj, change: Obj, index: Obj) -> Obj {
    let block = || {
        // Multipath ranged descriptors are supported (see BIP-389) .
        let desc_str: StrBuffer = descriptor.try_into()?;
        let change: bool = change.try_into()?; // for choosing external/internal derivation paths (AKA "change")
        let index: u32 = index.try_into()?; // for deriving specific public keys

        // Split multi-path descriptor into a vector of single-path descriptors.
        let descriptors = parse(&desc_str)
            .map_err(|_| Error::ValueError(c"Invalid descriptor"))?
            .into_single_descriptors()
            .map_err(|_| Error::ValueError(c"Multipath failed"))?;

        // Get the specified single-path descriptor.
        let ranged = descriptors
            .into_iter()
            .nth(change.into())
            .ok_or_else(|| Error::ValueErrorParam(c"Missing path", change.into()))?;

        // Derive the specified public keys (via BIP-32).
        let derived = {
            let secp = Secp256k1::verification_only();
            ranged
                .derived_descriptor(&secp, index)
                .map_err(|_| Error::ValueError(c"Failed to derive"))?
        };

        // Address formatting will be done in MicroPython.
        derived.explicit_script().unwrap().as_bytes().try_into()
    };
    unsafe { util::try_or_raise(block) }
}

// ---------------------------------------------------------------------------
// Module definition
// ---------------------------------------------------------------------------

#[no_mangle]
pub static mp_module_trezorminiscript: Module = obj_module! {
    /// def compile(descriptor: str, change: bool, index: int) -> bytes:
    ///     """Parse a Bitcoin multipath ranged output descriptor
    ///        and return the witness script bytes."""
    Qstr::MP_QSTR_compile => obj_fn_3!(upy_compile_descriptor).as_obj(),

    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezorminiscript.to_obj()
};
