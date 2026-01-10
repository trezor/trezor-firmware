use crate::{error::Error, strutil::TString};

#[cfg(feature = "micropython")]
use crate::micropython::{
    macros::{obj_dict, obj_map, obj_type},
    obj::Obj,
    qstr::Qstr,
    simple_type::SimpleTypeObj,
    typ::Type,
};

/// Homescreen notification.
#[derive(Clone)]
#[cfg_attr(test, derive(Debug))]
pub struct Notification {
    pub text: TString<'static>,
    pub level: NotificationLevel,
}

impl Notification {
    pub fn new(text: TString<'static>, level: NotificationLevel) -> Self {
        Self { text, level }
    }
}

/// Notification level determining the style of notification.
#[repr(u8)]
#[derive(Clone, Copy, Debug)]
pub enum NotificationLevel {
    /// Strong warning, e.g. "Backup failed"
    Alert = 0,
    /// Warning, e.g. "PIN not set"
    Warning = 1,
    /// Information, e.g. "Connected" or "Experimental features"
    Info = 2,
    /// Successful operation, e.g. "Coinjoin authorized"
    Success = 3,
}

impl TryFrom<u8> for NotificationLevel {
    type Error = Error;
    fn try_from(value: u8) -> Result<Self, Self::Error> {
        match value {
            0 => Ok(NotificationLevel::Alert),
            1 => Ok(NotificationLevel::Warning),
            2 => Ok(NotificationLevel::Info),
            3 => Ok(NotificationLevel::Success),
            _ => Err(Error::OutOfRange),
        }
    }
}

#[cfg(feature = "micropython")]
impl TryFrom<Obj> for NotificationLevel {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        let val = u8::try_from(obj)?;
        let this = Self::try_from(val)?;
        Ok(this)
    }
}

#[cfg(feature = "micropython")]
static NOTIFICATION_LEVEL_TYPE: Type = obj_type! {
    name: Qstr::MP_QSTR_NotificationLevel,
    locals: &obj_dict!(obj_map! {
        Qstr::MP_QSTR_ALERT => Obj::small_int(0),
        Qstr::MP_QSTR_WARNING => Obj::small_int(1),
        Qstr::MP_QSTR_INFO => Obj::small_int(2),
        Qstr::MP_QSTR_SUCCESS => Obj::small_int(3),
    }),
};

#[cfg(feature = "micropython")]
pub static NOTIFICATION_LEVEL_OBJ: SimpleTypeObj = SimpleTypeObj::new(&NOTIFICATION_LEVEL_TYPE);
