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
    micropython::{buffer::StrBuffer, module::Module, obj::Obj, qstr::Qstr, util},
};

#[global_allocator]
static MINISCRIPT_ALLOCATOR: emballoc::Allocator<{ 40 << 10 }> = emballoc::Allocator::new();

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

pub extern "C" fn upy_compile_descriptor(desc_obj: Obj, change_obj: Obj, index_obj: Obj) -> Obj {
    let block = || {
        // Multipath ranged descriptors are supported (see BIP-389) .
        let desc_str: StrBuffer = desc_obj.try_into()?;
        let change: u32 = change_obj.try_into()?; // for choosing external/internal derivation paths (AKA "change")
        let change = change % 2 == 1; // HACK: Liana uses <0;1>, <2;3>, <4;5> indices if a signer is reused.
        let index: u32 = index_obj.try_into()?; // for deriving specific public keys

        // Split multi-path descriptor into a vector of single-path descriptors.
        let descriptors = parse(&desc_str)
            .map_err(|_| Error::ValueErrorParam(c"Invalid descriptor", desc_obj))?
            .into_single_descriptors()
            .map_err(|_| Error::ValueErrorParam(c"Multipath failed", desc_obj))?;

        // Get the specified single-path descriptor.
        let ranged = descriptors
            .into_iter()
            .nth(change.into())
            .ok_or(Error::ValueErrorParam(c"Missing path", change_obj))?;

        // Derive the specified public keys (via BIP-32).
        let derived = {
            let secp = Secp256k1::verification_only();
            ranged
                .derived_descriptor(&secp, index)
                .map_err(|_| Error::ValueErrorParam(c"Failed to derive", index_obj))?
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
    /// def compile(descriptor: str, change: int, index: int) -> bytes:
    ///     """Parse a Bitcoin multipath ranged output descriptor
    ///        and return the witness script bytes."""
    Qstr::MP_QSTR_compile => obj_fn_3!(upy_compile_descriptor).as_obj(),

    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezorminiscript.to_obj()
};
