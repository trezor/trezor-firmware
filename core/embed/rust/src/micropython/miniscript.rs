extern crate alloc;

use crate::micropython::buffer::StrBuffer;
use crate::micropython::error::Error;
use crate::micropython::module::Module;
use crate::micropython::obj::Obj;
use crate::micropython::qstr::Qstr;
use crate::micropython::util;

// TODO: better error handling?
impl From<crate::miniscript::Error> for Error {
    fn from(_: crate::miniscript::Error) -> Self {
        Self::ValueError(c"Invalid miniscript")
    }
}

extern "C" fn upy_compile(desc_obj: Obj, internal_obj: Obj, index_obj: Obj) -> Obj {
    // TODO: run GC before starting parsing
    let block = || {
        let desc_str: StrBuffer = desc_obj.try_into()?;
        let internal = internal_obj.try_into()?; // for choosing external/internal derivation paths (AKA "change"),
        let index = index_obj.try_into()?;
        crate::miniscript::compile(&desc_str, internal, index)?
            .as_bytes()
            .try_into()
    };
    // TODO: make sure tracked memory didn't leak
    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
pub static mp_module_trezorminiscript: Module = obj_module! {
    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezorminiscript.to_obj(),

    /// def compile(descriptor: str, internal: bool, index: int) -> bytes:
    ///     """Compile a Miniscript multipath descriptor into an explicit script."""
    Qstr::MP_QSTR_compile => obj_fn_3!(upy_compile).as_obj(),
};
