use miniscript::bitcoin::hashes::{hash160, ripemd160, sha256};
use miniscript::{hash256, SerializedPublicKey, TranslateErr, Translator};

use crate::micropython::buffer::{get_buffer, StrBuffer};
use crate::micropython::error::Error;
use crate::micropython::list::List;
use crate::micropython::module::Module;
use crate::micropython::obj::Obj;
use crate::micropython::qstr::Qstr;
#[cfg(feature = "tracked_allocator")]
use crate::micropython::tracked_allocator::with_alloc;
/// Dummy implementation for tests
#[cfg(test)]
fn with_alloc<F, R>(f: F) -> R
where
    F: FnOnce() -> R,
{
    f()
}

use crate::micropython::util;
use crate::miniscript::{Descriptor, KeyExpr};

// TODO: better error handling?
impl From<crate::miniscript::Error> for Error {
    fn from(e: crate::miniscript::Error) -> Self {
        match e {
            crate::miniscript::Error::Unsupported => Error::NotImplementedError,
            crate::miniscript::Error::Invalid => Error::ValueError(c"Invalid miniscript"),
        }
    }
}

impl KeyExpr {
    fn as_tuple(&self) -> (Obj, Obj, Obj) {
        (self.key.into(), self.child.0.into(), self.child.1.into())
    }
}

struct Derive {
    func_obj: Obj,
}

impl Translator<KeyExpr> for Derive {
    type TargetPk = SerializedPublicKey;
    type Error = Error;

    fn pk(&mut self, k: &KeyExpr) -> Result<Self::TargetPk, Self::Error> {
        let args = [k.key.into(), k.child.0.into(), k.child.1.into()];
        // TODO: safety semantics of `self.func_obj`
        let buf: Obj = self.func_obj.call_with_n_args(&args)?;
        // SAFETY: reference is discarded at the end of the block
        let buf_slice: &[u8] = unsafe { get_buffer(buf)? };
        SerializedPublicKey::from_slice(buf_slice)
            .map_err(|_| Error::RuntimeError(c"Invalid pubkey"))
    }

    fn sha256(&mut self, _sha256: &sha256::Hash) -> Result<sha256::Hash, Self::Error> {
        Err(Error::NotImplementedError)
    }

    fn hash256(&mut self, _hash256: &hash256::Hash) -> Result<hash256::Hash, Self::Error> {
        Err(Error::NotImplementedError)
    }

    fn ripemd160(&mut self, _ripemd160: &ripemd160::Hash) -> Result<ripemd160::Hash, Self::Error> {
        Err(Error::NotImplementedError)
    }

    fn hash160(&mut self, _hash160: &hash160::Hash) -> Result<hash160::Hash, Self::Error> {
        Err(Error::NotImplementedError)
    }
}

impl From<TranslateErr<Error>> for Error {
    fn from(e: TranslateErr<Error>) -> Self {
        match e {
            // pk() failed (e.g. `func_obj` raised)
            TranslateErr::TranslatorErr(e) => e,
            // the resulting miniscript is invalid
            TranslateErr::OuterError(e) => crate::miniscript::Error::from(e).into(),
        }
    }
}

extern "C" fn upy_compile(desc_obj: Obj, func_obj: Obj) -> Obj {
    // TODO: run GC before starting parsing
    let block = || {
        let desc_str: StrBuffer = desc_obj.try_into()?;
        with_alloc(|| {
            // Heap allocation is needed for miniscript parsing and script compilation
            let script = Descriptor::parse(&desc_str)?
                .translate_pk(&mut Derive { func_obj })?
                .inner_script();
            Obj::try_from(script.as_bytes())
        })
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn upy_collect_keys(desc_obj: Obj) -> Obj {
    // TODO: run GC before starting parsing
    let block = || {
        let desc_str: StrBuffer = desc_obj.try_into()?;
        let mut list = List::with_capacity(0)?;
        with_alloc(|| {
            // Heap allocation is needed for miniscript parsing
            Descriptor::<KeyExpr>::parse(&desc_str)?
                .try_for_each(|k| list.append(Obj::try_from(k.as_tuple())?))
        })?;
        Ok(list.leak().into())
    };
    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
pub static mp_module_trezorminiscript: Module = obj_module! {
    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezorminiscript.to_obj(),

    /// def collect_keys(descriptor: str) -> list[tuple[int, int, int]]:
    ///     """Collect all key expressions from a Miniscript descriptor."""
    Qstr::MP_QSTR_collect_keys => obj_fn_1!(upy_collect_keys).as_obj(),

    /// def compile(descriptor: str, derive_fn: Callable[[int, int, int], bytes]) -> bytes:
    ///     """Compile a Miniscript multipath descriptor into an explicit script."""
    Qstr::MP_QSTR_compile => obj_fn_2!(upy_compile).as_obj(),
};
