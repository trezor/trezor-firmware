#[cfg(not(feature = "clippy"))]
use crate::ui::component::{
    text::paragraphs::{ParagraphSource, Paragraphs},
    Component, Timeout,
};
use crate::{
    error::Error,
    micropython::{obj::Obj, util::new_tuple},
    ui::layout::{
        device_menu_result::*,
        obj::ComponentMsgObj,
        result::{CANCELLED, CONFIRMED, INFO},
    },
};

use super::firmware::{
    AllowedTextContent, ConfirmHomescreen, ConfirmHomescreenMsg, DeviceMenuMsg, DeviceMenuScreen,
    Homescreen, HomescreenMsg, MnemonicInput, MnemonicKeyboard, MnemonicKeyboardMsg, PinKeyboard,
    PinKeyboardMsg, ProgressScreen, SelectWordCountMsg, SelectWordCountScreen, SelectWordMsg,
    SelectWordScreen, SetBrightnessScreen, TextScreen, TextScreenMsg, ValueInput, ValueInputScreen,
    ValueInputScreenMsg,
};

impl ComponentMsgObj for PinKeyboard<'_> {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            PinKeyboardMsg::Confirmed => self.pin().try_into(),
            PinKeyboardMsg::Cancelled => Ok(CANCELLED.as_obj()),
        }
    }
}

impl<T> ComponentMsgObj for MnemonicKeyboard<T>
where
    T: MnemonicInput,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            MnemonicKeyboardMsg::Confirmed => {
                if let Some(word) = self.mnemonic() {
                    word.try_into()
                } else {
                    fatal_error!("Invalid mnemonic")
                }
            }
            MnemonicKeyboardMsg::Previous => "".try_into(),
        }
    }
}

// Clippy/compiler complains about conflicting implementations
// TODO move the common impls to a common module
#[cfg(not(feature = "clippy"))]
impl<'a, T> ComponentMsgObj for Paragraphs<T>
where
    T: ParagraphSource<'a>,
{
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!()
    }
}

// Clippy/compiler complains about conflicting implementations
#[cfg(not(feature = "clippy"))]
impl<T> ComponentMsgObj for (Timeout, T)
where
    T: Component<Msg = ()>,
{
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        Ok(CANCELLED.as_obj())
    }
}

impl ComponentMsgObj for Homescreen {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            HomescreenMsg::Dismissed => Ok(CANCELLED.as_obj()),
            HomescreenMsg::Menu => Ok(INFO.as_obj()),
        }
    }
}

impl ComponentMsgObj for ProgressScreen {
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!()
    }
}

impl<T> ComponentMsgObj for TextScreen<T>
where
    T: AllowedTextContent,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            TextScreenMsg::Cancelled => Ok(CANCELLED.as_obj()),
            TextScreenMsg::Confirmed => Ok(CONFIRMED.as_obj()),
            TextScreenMsg::Menu => Ok(INFO.as_obj()),
        }
    }
}

impl ComponentMsgObj for SelectWordScreen {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            SelectWordMsg::Selected(i) => i.try_into(),
            SelectWordMsg::Cancelled => Ok(CANCELLED.as_obj()),
        }
    }
}

impl ComponentMsgObj for SelectWordCountScreen {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            SelectWordCountMsg::Selected(i) => i.try_into(),
            SelectWordCountMsg::Cancelled => Ok(CANCELLED.as_obj()),
        }
    }
}

impl<T: ValueInput> ComponentMsgObj for ValueInputScreen<T> {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            ValueInputScreenMsg::Confirmed(i) => i.try_into(),
            ValueInputScreenMsg::Cancelled => Ok(CANCELLED.as_obj()),
            // menu message is handled only in the flow
            ValueInputScreenMsg::Menu => unreachable!(),
            // changed value message is handled only in the flow
            ValueInputScreenMsg::Changed(_) => unreachable!(),
        }
    }
}

impl ComponentMsgObj for ConfirmHomescreen {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            ConfirmHomescreenMsg::Cancelled => Ok(CANCELLED.as_obj()),
            ConfirmHomescreenMsg::Confirmed => Ok(CONFIRMED.as_obj()),
        }
    }
}

impl ComponentMsgObj for SetBrightnessScreen {
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        Ok(CONFIRMED.as_obj())
    }
}

impl<'a> ComponentMsgObj for DeviceMenuScreen<'a> {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            DeviceMenuMsg::BackupFailed => Ok(BACKUP_FAILED.as_obj()),
            DeviceMenuMsg::DevicePair => Ok(DEVICE_PAIR.as_obj()),
            DeviceMenuMsg::DeviceDisconnect(index) => {
                Ok(new_tuple(&[DEVICE_DISCONNECT.as_obj(), index.try_into()?])?)
            }
            DeviceMenuMsg::CheckBackup => Ok(CHECK_BACKUP.as_obj()),
            DeviceMenuMsg::WipeDevice => Ok(WIPE_DEVICE.as_obj()),
            DeviceMenuMsg::DeviceName => Ok(DEVICE_NAME.as_obj()),
            DeviceMenuMsg::ScreenBrightness => Ok(SCREEN_BRIGHTNESS.as_obj()),
            DeviceMenuMsg::AutoLockDelay => Ok(AUTO_LOCK_DELAY.as_obj()),
            DeviceMenuMsg::Led => Ok(LED.as_obj()),
            DeviceMenuMsg::Close => Ok(CANCELLED.as_obj()),
        }
    }
}
