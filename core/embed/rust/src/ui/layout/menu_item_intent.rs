use crate::error::Error;
#[cfg(feature = "micropython")]
use crate::micropython::{
    macros::{obj_dict, obj_map, obj_type},
    obj::Obj,
    qstr::Qstr,
    simple_type::SimpleTypeObj,
    typ::FullType,
};

/// What a menu entry means, which each model renders in its own way.
#[repr(u8)]
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum MenuItemIntent {
    /// An ordinary entry.
    Standard = 0,
    /// An entry with destructive consequences, e.g. cancelling a signature.
    Danger = 1,
}

impl TryFrom<u8> for MenuItemIntent {
    type Error = Error;
    fn try_from(value: u8) -> Result<Self, Self::Error> {
        match value {
            0 => Ok(MenuItemIntent::Standard),
            1 => Ok(MenuItemIntent::Danger),
            _ => Err(Error::OutOfRange),
        }
    }
}

#[cfg(feature = "micropython")]
impl TryFrom<Obj> for MenuItemIntent {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        Self::try_from(u8::try_from(obj)?)
    }
}

#[cfg(feature = "micropython")]
static MENU_ITEM_INTENT_TYPE: FullType = obj_type! {
    name: Qstr::MP_QSTR_MenuItemIntent,
    locals: &obj_dict!(obj_map! {
        Qstr::MP_QSTR_STANDARD => Obj::small_int(MenuItemIntent::Standard as u16),
        Qstr::MP_QSTR_DANGER => Obj::small_int(MenuItemIntent::Danger as u16),
    }),
};

#[cfg(feature = "micropython")]
pub static MENU_ITEM_INTENT_OBJ: SimpleTypeObj = SimpleTypeObj::new(&MENU_ITEM_INTENT_TYPE);
