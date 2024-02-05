use crate::micropython::{qstr::Qstr, simple_type::SimpleTypeObj, typ::Type};

static CONFIRMED_TYPE: Type = obj_type! { name: Qstr::MP_QSTR_CONFIRMED, };
static CANCELLED_TYPE: Type = obj_type! { name: Qstr::MP_QSTR_CANCELLED, };
static INFO_TYPE: Type = obj_type! { name: Qstr::MP_QSTR_INFO, };

pub static CONFIRMED: SimpleTypeObj = SimpleTypeObj::new(&CONFIRMED_TYPE);
pub static CANCELLED: SimpleTypeObj = SimpleTypeObj::new(&CANCELLED_TYPE);
pub static INFO: SimpleTypeObj = SimpleTypeObj::new(&INFO_TYPE);
