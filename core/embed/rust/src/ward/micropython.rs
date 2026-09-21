use crate::micropython::macros::obj_module;
use crate::micropython::module::Module;
use crate::micropython::qstr::Qstr;

#[no_mangle]
pub static mp_module_trezorward: Module = obj_module! {
    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezorward.to_obj()
};
