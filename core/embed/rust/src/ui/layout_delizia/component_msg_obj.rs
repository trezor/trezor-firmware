use core::convert::TryInto;

use super::component::{
    AddressDetails, CoinJoinProgress, Frame, FrameMsg, Homescreen, HomescreenMsg, Lockscreen,
    MnemonicInput, MnemonicKeyboard, MnemonicKeyboardMsg, PinKeyboard, PinKeyboardMsg, Progress,
    PromptScreen, SelectWordCount, SelectWordCountMsg, StatusScreen, SwipeContent, SwipeUpScreen,
    SwipeUpScreenMsg, VerticalMenu, VerticalMenuChoiceMsg,
};
use crate::{
    error::Error,
    micropython::obj::Obj,
    ui::{
        component::{
            text::paragraphs::{ParagraphSource, Paragraphs},
            Component, Never, Timeout,
        },
        flow::Swipable,
        layout::{
            obj::ComponentMsgObj,
            result::{CANCELLED, CONFIRMED},
        },
    },
};

impl TryFrom<SelectWordCountMsg> for Obj {
    type Error = Error;

    fn try_from(value: SelectWordCountMsg) -> Result<Self, Self::Error> {
        match value {
            SelectWordCountMsg::Selected(i) => i.try_into(),
        }
    }
}

impl TryFrom<VerticalMenuChoiceMsg> for Obj {
    type Error = Error;

    fn try_from(value: VerticalMenuChoiceMsg) -> Result<Self, Self::Error> {
        match value {
            VerticalMenuChoiceMsg::Selected(i) => i.try_into(),
        }
    }
}

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

impl<T> ComponentMsgObj for Frame<T>
where
    T: ComponentMsgObj,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            FrameMsg::Content(c) => self.inner().msg_try_into_obj(c),
            FrameMsg::Button(b) => b.try_into(),
        }
    }
}

impl ComponentMsgObj for SelectWordCount {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            SelectWordCountMsg::Selected(n) => n.try_into(),
        }
    }
}

impl ComponentMsgObj for VerticalMenu {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            VerticalMenuChoiceMsg::Selected(i) => i.try_into(),
        }
    }
}

impl ComponentMsgObj for StatusScreen {
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        Ok(CONFIRMED.as_obj())
    }
}

impl ComponentMsgObj for PromptScreen {
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        Ok(CONFIRMED.as_obj())
    }
}

impl<T: Component + ComponentMsgObj> ComponentMsgObj for SwipeContent<T> {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        self.inner().msg_try_into_obj(msg)
    }
}

impl<T: Component + ComponentMsgObj + Swipable> ComponentMsgObj for SwipeUpScreen<T> {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            SwipeUpScreenMsg::Content(c) => self.inner().msg_try_into_obj(c),
            SwipeUpScreenMsg::Swiped => Ok(CONFIRMED.as_obj()),
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

impl ComponentMsgObj for Progress {
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!()
    }
}

impl ComponentMsgObj for Homescreen {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            HomescreenMsg::Dismissed => Ok(CANCELLED.as_obj()),
        }
    }
}

impl ComponentMsgObj for Lockscreen {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            HomescreenMsg::Dismissed => Ok(CANCELLED.as_obj()),
        }
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

impl ComponentMsgObj for AddressDetails {
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        Ok(CANCELLED.as_obj())
    }
}

impl<U> ComponentMsgObj for CoinJoinProgress<U>
where
    U: Component<Msg = Never>,
{
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!();
    }
}
