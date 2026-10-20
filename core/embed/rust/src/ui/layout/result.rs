#[cfg(feature = "app_loading")]
use trezor_app_sdk::structs::TrezorUiResult;

use crate::micropython::macros::obj_type;
use crate::micropython::qstr::Qstr;
use crate::micropython::simple_type::SimpleTypeObj;
use crate::micropython::typ::FullType;
#[cfg(feature = "app_loading")]
use crate::micropython::{Error, Obj};

static CONFIRMED_TYPE: FullType = obj_type! { name: Qstr::MP_QSTR_CONFIRMED, };
static CANCELLED_TYPE: FullType = obj_type! { name: Qstr::MP_QSTR_CANCELLED, };
static BACK_TYPE: FullType = obj_type! { name: Qstr::MP_QSTR_BACK, };
static INFO_TYPE: FullType = obj_type! { name: Qstr::MP_QSTR_INFO, };

pub static CONFIRMED: SimpleTypeObj = SimpleTypeObj::new(&CONFIRMED_TYPE);
pub static CANCELLED: SimpleTypeObj = SimpleTypeObj::new(&CANCELLED_TYPE);
pub static BACK: SimpleTypeObj = SimpleTypeObj::new(&BACK_TYPE);
pub static INFO: SimpleTypeObj = SimpleTypeObj::new(&INFO_TYPE);

/// A layout's answer as the app receives it: the wire's [`TrezorUiResult`].
/// Only a decision crosses. A layout's own navigation (`INFO`, `BACK`) never
/// leaves core, so it is refused here.
///
/// WIP: an interim translation, the only place the layout results above meet
/// the wire's enum. The aim is one type all round: layouts return
/// `TrezorUiResult` for their decisions, these objects become its face in
/// Python (with `From<TrezorUiResult> for Obj` beside this), and `INFO` and
/// `BACK` move to a core-only navigation type of their own. That waits for the
/// per-model layouts to unify, so it is one rewrite rather than four. Until
/// then the chunk-paging answers (`Forward`, `Backward`, `ConfirmedAll`) have
/// no layout result to come from: no screen can tell it is at a chunk's edge.
#[cfg(feature = "app_loading")]
impl TryFrom<Obj> for TrezorUiResult {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        if obj == CONFIRMED.as_obj() {
            Ok(Self::Confirmed)
        } else if obj == CANCELLED.as_obj() {
            Ok(Self::Cancelled)
        } else {
            Err(Error::ValueError(c"not an answer for an app"))
        }
    }
}
