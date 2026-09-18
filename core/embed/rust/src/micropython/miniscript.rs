use crate::micropython::buffer::{get_buffer, StrBuffer};
use crate::micropython::error::Error;
use crate::micropython::module::Module;
use crate::micropython::obj::Obj;
use crate::micropython::qstr::Qstr;
use crate::micropython::tracked_allocator::with_alloc;
use crate::micropython::util;

extern crate alloc;

use alloc::string::String;

use miniscript::bitcoin::hashes::{hash160, ripemd160, sha256};
use miniscript::bitcoin::{PublicKey, ScriptBuf};
use miniscript::{hash256, TranslateErr, Translator};

// TODO: better error handling?
impl From<crate::miniscript::Error> for Error {
    fn from(_: crate::miniscript::Error) -> Self {
        Self::ValueError(c"Invalid miniscript")
    }
}

struct Derive(Obj);

impl Translator<String> for Derive {
    type TargetPk = PublicKey;
    type Error = Error;

    fn pk(&mut self, pk: &String) -> Result<Self::TargetPk, Self::Error> {
        // TODO: check global xpubs structure
        // TODO: avoid cloning
        let buf: Obj = self.0.call_with_n_args(&[pk.as_str().try_into()?])?;
        // SAFETY: reference is discarded at the end of the block
        let buf_slice: &[u8] = unsafe { get_buffer(buf)? };
        // TODO: check compression?
        PublicKey::from_slice(buf_slice).map_err(|_| Error::RuntimeError(c"Bad pubkey"))
    }

    fn sha256(&mut self, _sha256: &String) -> Result<sha256::Hash, Error> {
        Err(Error::NotImplementedError)
    }

    fn hash256(&mut self, _hash256: &String) -> Result<hash256::Hash, Error> {
        Err(Error::NotImplementedError)
    }

    fn ripemd160(&mut self, _ripemd160: &String) -> Result<ripemd160::Hash, Error> {
        Err(Error::NotImplementedError)
    }

    fn hash160(&mut self, _hash160: &String) -> Result<hash160::Hash, Error> {
        Err(Error::NotImplementedError)
    }
}

fn compile(desc: &str, mut derive: Derive) -> Result<ScriptBuf, Error> {
    let multipath = crate::miniscript::Descriptor::parse(&desc)?;
    match multipath.translate_pk(&mut derive) {
        Ok(desc) => Ok(desc.inner_script()),
        Err(TranslateErr::TranslatorErr(e)) => Err(e), // translator failed
        Err(TranslateErr::OuterError(e)) => Err(crate::miniscript::Error::Miniscript(e).into()), /* invalid translation result */
    }
}

extern "C" fn upy_compile(desc_obj: Obj, derive_obj: Obj) -> Obj {
    // TODO: run GC before starting parsing
    let block = || {
        let desc_str: StrBuffer = desc_obj.try_into()?;

        // Heap allocation is needed for miniscript parsing and script compilation:
        with_alloc(|| {
            compile(&desc_str, Derive(derive_obj))
                .and_then(|script| Obj::try_from(script.as_bytes()))
        })
    };
    // TODO: make sure tracked memory didn't leak
    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
pub static mp_module_trezorminiscript: Module = obj_module! {
    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezorminiscript.to_obj(),

    /// def compile(descriptor: str, derive_fn: Callable[[str], bytes]) -> bytes:
    ///     """Compile a Miniscript multipath descriptor into an explicit script."""
    Qstr::MP_QSTR_compile => obj_fn_2!(upy_compile).as_obj(),
};
