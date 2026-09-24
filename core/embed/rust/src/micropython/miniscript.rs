extern crate alloc;

use miniscript::bitcoin::secp256k1::Secp256k1;
use miniscript::bitcoin::ScriptBuf;
use miniscript::descriptor::{Descriptor, DescriptorPublicKey, Wsh};
use miniscript::expression::{FromTree, Tree};

use crate::micropython::buffer::StrBuffer;
use crate::micropython::error::Error;
use crate::micropython::module::Module;
use crate::micropython::obj::Obj;
use crate::micropython::qstr::Qstr;
use crate::micropython::util;

// TODO: better error handling?
impl From<miniscript::Error> for Error {
    fn from(value: miniscript::Error) -> Self {
        log::error!("Invalid miniscript: {}", value);
        Self::ValueError(c"Invalid miniscript")
    }
}

fn parse(desc_str: &str) -> Result<Descriptor<DescriptorPublicKey>, Error> {
    let desc = {
        let tree = Tree::from_str(desc_str)?;
        log::trace!("tree");
        let top = tree.root();
        match (top.name(), top.n_children()) {
            ("wsh", 1) => Descriptor::Wsh(Wsh::from_tree(top)?),
            _ => return Err(Error::NotImplementedError),
        }
    };
    log::trace!("valid");
    desc.sanity_check()?; // we don't support insane descriptors
    log::trace!("sane");
    Ok(desc)
}

fn derive(
    multipath: Descriptor<DescriptorPublicKey>,
    internal: bool,
    index: u32,
) -> Result<ScriptBuf, Error> {
    let ranged = multipath
        .into_single_descriptors()?
        .into_iter()
        .nth(internal.into())
        .ok_or(Error::ValueError(c"Missing path"))?;
    // Derive the specified public keys (via BIP-32).
    let derived = ranged
        .derived_descriptor(&Secp256k1::verification_only(), index)
        .map_err(|_| Error::ValueError(c"Derivation failed"))?;
    // Address formatting will be done in MicroPython.
    Ok(derived.explicit_script()?)
}

extern "C" fn upy_compile(desc_obj: Obj, internal_obj: Obj, index_obj: Obj) -> Obj {
    // TODO: run GC before starting parsing
    let block = || {
        let desc_str: StrBuffer = desc_obj.try_into()?;
        let internal: bool = internal_obj.try_into()?; // for choosing external/internal derivation paths (AKA "change")
        let index: u32 = index_obj.try_into()?;
        let script = derive(parse(&desc_str)?, internal, index)?;
        script.as_bytes().try_into()
    };
    // TODO: make sure tracked memory didn't leak
    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
pub static mp_module_trezorminiscript: Module = obj_module! {
    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezorminiscript.to_obj(),

    /// def compile(descriptor: str, internal: bool, index: int) -> None:
    ///     """Parse a Miniscript descriptor."""
    Qstr::MP_QSTR_compile => obj_fn_3!(upy_compile).as_obj(),
};
