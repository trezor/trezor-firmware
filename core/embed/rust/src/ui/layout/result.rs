use crate::micropython::macros::obj_type;
use crate::micropython::qstr::Qstr;
use crate::micropython::simple_type::SimpleTypeObj;
use crate::micropython::typ::FullType;

static CONFIRMED_TYPE: FullType = obj_type! { name: Qstr::MP_QSTR_CONFIRMED, };
static CANCELLED_TYPE: FullType = obj_type! { name: Qstr::MP_QSTR_CANCELLED, };
static BACK_TYPE: FullType = obj_type! { name: Qstr::MP_QSTR_BACK, };
static INFO_TYPE: FullType = obj_type! { name: Qstr::MP_QSTR_INFO, };

pub static CONFIRMED: SimpleTypeObj = SimpleTypeObj::new(&CONFIRMED_TYPE);
pub static CANCELLED: SimpleTypeObj = SimpleTypeObj::new(&CANCELLED_TYPE);
pub static BACK: SimpleTypeObj = SimpleTypeObj::new(&BACK_TYPE);
pub static INFO: SimpleTypeObj = SimpleTypeObj::new(&INFO_TYPE);
