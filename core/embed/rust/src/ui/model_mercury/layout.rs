use core::{cmp::Ordering, convert::TryInto};
use heapless::Vec;

use super::{
    component::{
        AddressDetails, Bip39Input, CoinJoinProgress, Frame, FrameMsg, Homescreen, HomescreenMsg,
        Lockscreen, MnemonicInput, MnemonicKeyboard, MnemonicKeyboardMsg, PinKeyboard,
        PinKeyboardMsg, Progress, PromptScreen, SelectWordCount, SelectWordCountMsg, Slip39Input,
        StatusScreen, SwipeUpScreen, SwipeUpScreenMsg, VerticalMenu, VerticalMenuChoiceMsg,
    },
    flow::{self},
    theme,
};
use crate::{
    error::{value_error, Error},
    io::BinaryData,
    micropython::{
        iter::IterBuf,
        macros::{obj_fn_0, obj_fn_1, obj_fn_kw, obj_module},
        map::Map,
        module::Module,
        obj::Obj,
        qstr::Qstr,
        util,
    },
    strutil::TString,
    translations::TR,
    trezorhal::model,
    ui::{
        backlight::BACKLIGHT_LEVELS_OBJ,
        component::{
            base::ComponentExt,
            connect::Connect,
            swipe_detect::SwipeSettings,
            text::{
                op::OpTextLayout,
                paragraphs::{
                    Checklist, Paragraph, ParagraphSource, ParagraphVecLong, ParagraphVecShort,
                    Paragraphs, VecExt,
                },
                TextStyle,
            },
            Border, CachedJpeg, Component, FormattedText, Never, Timeout,
        },
        flow::Swipable,
        geometry::{self, Direction},
        layout::{
            base::LAYOUT_STATE,
            obj::{ComponentMsgObj, LayoutObj, ATTACH_TYPE_OBJ},
            result::{CANCELLED, CONFIRMED, INFO},
            util::{upy_disable_animation, PropsList, RecoveryType},
        },
        model_mercury::{
            component::{check_homescreen_format, SwipeContent},
            flow::{
                new_confirm_action_simple,
                util::{ConfirmBlobParams, ShowInfoParams},
                ConfirmActionExtra, ConfirmActionMenuStrings, ConfirmActionStrings,
            },
            theme::ICON_BULLET_CHECKMARK,
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

#[no_mangle]
pub static mp_module_trezorui2: Module = obj_module! {
    /// from trezor import utils
    /// from trezorui_api import *
    ///
    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezorui2.to_obj(),

};
