use miniscript::bitcoin::PublicKey;
use miniscript::{TranslateErr, Translator};

use crate::micropython::buffer::{get_buffer, StrBuffer};
use crate::micropython::error::Error;
use crate::micropython::list::List;
use crate::micropython::module::Module;
use crate::micropython::obj::Obj;
use crate::micropython::qstr::Qstr;
use crate::micropython::tracked_allocator::with_alloc;
use crate::micropython::util;
use crate::miniscript::{Descriptor, KeyExpr};

// TODO: better error handling?
impl From<crate::miniscript::Error> for Error {
    fn from(_: crate::miniscript::Error) -> Self {
        Self::ValueError(c"Invalid miniscript")
    }
}

impl KeyExpr {
    fn as_tuple(&self) -> (Obj, Obj, Obj) {
        (
            self.key.into(),
            self.children.0.into(),
            self.children.1.into(),
        )
    }
}

struct Derive {
    func_obj: Obj,
}

impl Translator<KeyExpr> for Derive {
    type TargetPk = PublicKey;
    type Error = Error;

    fn pk(&mut self, k: &KeyExpr) -> Result<Self::TargetPk, Self::Error> {
        // TODO: check global xpubs structure
        // TODO: safety semantics of `self.func_obj`
        let buf: Obj = self.func_obj.call_with_n_args(&[
            k.key.into(),
            k.children.0.into(),
            k.children.1.into(),
        ])?;
        // SAFETY: reference is discarded at the end of the block
        let buf_slice: &[u8] = unsafe { get_buffer(buf)? };
        // TODO: check compression?
        PublicKey::from_slice(buf_slice).map_err(|_| Error::RuntimeError(c"Bad pubkey"))
    }
}

impl From<TranslateErr<Error>> for Error {
    fn from(e: TranslateErr<Error>) -> Self {
        match e {
            TranslateErr::TranslatorErr(e) => e,
            TranslateErr::OuterError(e) => e.into(),
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
