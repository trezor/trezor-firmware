use crate::micropython::module::Module;
use crate::micropython::qstr::Qstr;

#[no_mangle]
pub static mp_module_trezorminiscript: Module = obj_module! {
    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezorminiscript.to_obj()
};
