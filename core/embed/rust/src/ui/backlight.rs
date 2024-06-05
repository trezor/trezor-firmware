use crate::{
    error::Error,
    micropython::{
        ffi, macros::obj_type, obj::Obj, qstr::Qstr, simple_type::SimpleTypeObj, typ::Type, util,
    },
    ui::{ui_features::ModelUI, UIFeaturesCommon},
};

/*
 * This whole module should be removed, in favor of fully
 * moving backlight control into Rust. Relatively easy to do, but not
 * necessary right now. Filed as https://github.com/trezor/trezor-firmware/issues/3849
 *
 * Consider this module temporary. (yeah yeah everyone knows "temporary"
 * things stay forever. Written in May 2024.)
 */

static BACKLIGHT_LEVELS_TYPE: Type = obj_type! {
    name: Qstr::MP_QSTR_BacklightLevels,
    attr_fn: backlight_levels_attr,
};

unsafe extern "C" fn backlight_levels_attr(_self_in: Obj, attr: ffi::qstr, dest: *mut Obj) {
    let block = || {
        let arg = unsafe { dest.read() };
        if !arg.is_null() {
            // Null destination would mean a `setattr`.
            return Err(Error::TypeError);
        }
        let attr = Qstr::from_u16(attr as _);
        let value = match attr {
            Qstr::MP_QSTR_NONE => ModelUI::get_backlight_none(),
            Qstr::MP_QSTR_NORMAL => ModelUI::get_backlight_normal(),
            Qstr::MP_QSTR_LOW => ModelUI::get_backlight_low(),
            Qstr::MP_QSTR_DIM => ModelUI::get_backlight_dim(),
            Qstr::MP_QSTR_MAX => ModelUI::get_backlight_max(),
            _ => return Err(Error::AttributeError(attr)),
        };
        unsafe { dest.write(value.into()) };
        Ok(())
    };
    unsafe { util::try_or_raise(block) }
}

pub static BACKLIGHT_LEVELS_OBJ: SimpleTypeObj = SimpleTypeObj::new(&BACKLIGHT_LEVELS_TYPE);
