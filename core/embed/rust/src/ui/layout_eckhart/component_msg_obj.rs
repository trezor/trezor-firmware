use crate::{
    error::Error,
    micropython::obj::Obj,
    ui::{
        component::{
            text::paragraphs::{ParagraphSource, Paragraphs},
            Component, Timeout,
        },
        layout::{
            obj::ComponentMsgObj,
            result::{CANCELLED, CONFIRMED, INFO},
        },
    },
};

use super::firmware::{
    AllowedTextContent, ConfirmHomescreen, ConfirmHomescreenMsg, Homescreen, HomescreenMsg,
    MnemonicInput, MnemonicKeyboard, MnemonicKeyboardMsg, NumberInputScreen, NumberInputScreenMsg,
    PinKeyboard, PinKeyboardMsg, SelectWordCountMsg, SelectWordCountScreen, SelectWordMsg,
    SelectWordScreen, TextScreen, TextScreenMsg,
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
        }
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

impl ComponentMsgObj for NumberInputScreen {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            NumberInputScreenMsg::Confirmed(i) => i.try_into(),
            NumberInputScreenMsg::Cancelled => Ok(CANCELLED.as_obj()),
            NumberInputScreenMsg::Menu => Ok(INFO.as_obj()),
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
