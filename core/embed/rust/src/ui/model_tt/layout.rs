use core::convert::TryInto;

use crate::{
    error::Error,
    micropython::{buffer::Buffer, map::Map, module::Module, obj::Obj, qstr::Qstr},
    ui::{
        component::{
            base::ComponentExt,
            paginated::{PageMsg, Paginate},
            text::paragraphs::Paragraphs,
            Component,
            FormattedText
        },
        geometry::Dimensions,
        layout::{
            obj::{ComponentMsgObj, LayoutObj},
            result::{CANCELLED, CONFIRMED},
        },
    },
    util,
};

use super::{
    component::{
        Bip39Input, Button, ButtonMsg, DialogMsg, Frame, HoldToConfirm, HoldToConfirmMsg,
        MnemonicKeyboard, MnemonicKeyboardMsg, PassphraseKeyboard, PassphraseKeyboardMsg,
        PinKeyboard, PinKeyboardMsg, Slip39Input, SwipePage,
        Dialog
    },
    theme,
};

impl<T, U> ComponentMsgObj for Dialog<T, Button<U>, Button<U>>
where
    T: ComponentMsgObj,
    U: AsRef<[u8]>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            DialogMsg::Content(c) => Ok(self.inner().msg_try_into_obj(c)?),
            DialogMsg::Left(ButtonMsg::Clicked) => Ok(CANCELLED.as_obj()),
            DialogMsg::Right(ButtonMsg::Clicked) => Ok(CONFIRMED.as_obj()),
            _ => Ok(Obj::const_none()),
        }
    }
}

impl<T> ComponentMsgObj for HoldToConfirm<T>
where
    T: ComponentMsgObj,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            HoldToConfirmMsg::Content(c) => Ok(self.inner().msg_try_into_obj(c)?),
            HoldToConfirmMsg::Confirmed => Ok(CONFIRMED.as_obj()),
            HoldToConfirmMsg::Cancelled => Ok(CANCELLED.as_obj()),
        }
    }
}

impl TryFrom<PinKeyboardMsg> for Obj {
    type Error = Error;

    fn try_from(val: PinKeyboardMsg) -> Result<Self, Self::Error> {
        match val {
            PinKeyboardMsg::Confirmed => 1.try_into(),
            PinKeyboardMsg::Cancelled => 2.try_into(),
        }
    }
}

impl ComponentMsgObj for PinKeyboard {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            PinKeyboardMsg::Cancelled => Ok(CANCELLED.as_obj()),
            PinKeyboardMsg::Confirmed => self.pin().try_into(),
        }
    }
}

impl TryFrom<MnemonicKeyboardMsg> for Obj {
    type Error = Error;

    fn try_from(val: MnemonicKeyboardMsg) -> Result<Self, Self::Error> {
        match val {
            MnemonicKeyboardMsg::Confirmed => Ok(Obj::const_true()),
        }
    }
}

impl<T, U> ComponentMsgObj for Frame<T, U>
where
    T: ComponentMsgObj,
    U: AsRef<[u8]>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        self.inner().msg_try_into_obj(msg)
    }
}

impl<T, U> ComponentMsgObj for SwipePage<T, U>
where
    T: Component + Dimensions + Paginate,
    U: Component<Msg = bool>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            PageMsg::Content(_) => Err(Error::TypeError),
            PageMsg::Controls(true) => Ok(CONFIRMED.as_obj()),
            PageMsg::Controls(false) => Ok(CANCELLED.as_obj()),
        }
    }
}

impl TryFrom<PassphraseKeyboardMsg> for Obj {
    type Error = Error;

    fn try_from(val: PassphraseKeyboardMsg) -> Result<Self, Self::Error> {
        match val {
            PassphraseKeyboardMsg::Confirmed => Ok(Obj::const_true()),
            PassphraseKeyboardMsg::Cancelled => Ok(Obj::const_none()),
        }
    }
}

#[no_mangle]
extern "C" fn ui_layout_new_example(_param: Obj) -> Obj {
    let block = move || {
        let layout = LayoutObj::new(HoldToConfirm::new(
            FormattedText::new::<theme::TTDefaultText>(
                "Testing text layout, with some text, and some more text. And {param}",
            )
            .with(b"param", b"parameters!"),
        ))?;
        Ok(layout.into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn new_request_pin(_param: Obj) -> Obj {
    let block = move || {
        let layout = LayoutObj::new(PinKeyboard::new(theme::borders(), b"Enter PIN", b""))?;
        Ok(layout.into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn new_confirm_action(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: Buffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let action: Option<Buffer> = kwargs.get(Qstr::MP_QSTR_action)?.try_into_option()?;
        let description: Option<Buffer> =
            kwargs.get(Qstr::MP_QSTR_description)?.try_into_option()?;
        let verb: Option<Buffer> = kwargs.get(Qstr::MP_QSTR_verb)?.try_into_option()?;
        let reverse: bool = kwargs.get(Qstr::MP_QSTR_reverse)?.try_into()?;

        let paragraphs = {
            let action = action.unwrap_or_default();
            let description = description.unwrap_or_default();
            let mut paragraphs = Paragraphs::new();
            if !reverse {
                paragraphs = paragraphs
                    .add::<theme::TTDefaultText>(theme::FONT_BOLD, action)
                    .add::<theme::TTDefaultText>(theme::FONT_NORMAL, description);
            } else {
                paragraphs = paragraphs
                    .add::<theme::TTDefaultText>(theme::FONT_NORMAL, description)
                    .add::<theme::TTDefaultText>(theme::FONT_BOLD, action);
            }
            paragraphs
        };

        let buttons = Button::left_right(
            Button::with_icon(theme::ICON_CANCEL),
            |msg| (matches!(msg, ButtonMsg::Clicked)).then(|| false),
            Button::with_text(verb.unwrap_or_else(|| "CONFIRM".into()))
                .styled(theme::button_confirm()),
            |msg| (matches!(msg, ButtonMsg::Clicked)).then(|| true),
        );

        let obj = LayoutObj::new(
            Frame::new(title, SwipePage::new(paragraphs, buttons, theme::BG)).into_child(),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

#[no_mangle]
extern "C" fn ui_layout_new_pin(n_args: usize, args: *const Obj, kwargs: *const Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let prompt: Buffer = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let subprompt: Buffer = kwargs.get(Qstr::MP_QSTR_subprompt)?.try_into()?;
        let allow_cancel: Option<bool> =
            kwargs.get(Qstr::MP_QSTR_allow_cancel)?.try_into_option()?;
        let warning: Option<Buffer> = kwargs.get(Qstr::MP_QSTR_warning)?.try_into_option()?;
        let obj = LayoutObj::new(
            PinKeyboard::new(prompt, subprompt, warning, allow_cancel.unwrap_or(true)).into_child(),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

#[no_mangle]
extern "C" fn ui_layout_new_passphrase(n_args: usize, args: *const Obj, kwargs: *const Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let _prompt: Buffer = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let _max_len: u32 = kwargs.get(Qstr::MP_QSTR_max_len)?.try_into()?;
        let obj = LayoutObj::new(PassphraseKeyboard::new().into_child())?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

#[no_mangle]
extern "C" fn ui_layout_new_bip39(n_args: usize, args: *const Obj, kwargs: *const Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let _prompt: Buffer = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let obj = LayoutObj::new(
            MnemonicKeyboard::new(Bip39Input::new(), b"Type word 11 of 12").into_child(),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

#[no_mangle]
extern "C" fn ui_layout_new_slip39(n_args: usize, args: *const Obj, kwargs: *const Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let _prompt: Buffer = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let obj = LayoutObj::new(
            MnemonicKeyboard::new(Slip39Input::new(), b"Type word 13 of 20").into_child(),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

#[no_mangle]
pub static mp_module_trezorui2: Module = obj_module! {
    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezorui2.to_obj(),

    /// CONFIRMED: object
    Qstr::MP_QSTR_CONFIRMED => CONFIRMED.as_obj(),

    /// CANCELLED: object
    Qstr::MP_QSTR_CANCELLED => CANCELLED.as_obj(),

    /// def confirm_action(
    ///     *,
    ///     title: str,
    ///     action: str | None = None,
    ///     description: str | None = None,
    ///     verb: str | None = None,
    ///     verb_cancel: str | None = None,
    ///     hold: bool | None = None,
    ///     reverse: bool = False,
    /// ) -> object:
    ///     """Confirm action."""
    Qstr::MP_QSTR_confirm_action => obj_fn_kw!(0, new_confirm_action).as_obj(),

    /// def request_pin(
    ///     *,
    ///     prompt: str,
    ///     subprompt: str | None = None,
    ///     allow_cancel: bool = True,
    ///     warning: str | None = None,
    /// ) -> str:
    ///     """Request pin on device."
    Qstr::MP_QSTR_request_pin => obj_fn_1!(new_request_pin).as_obj(),
};

#[cfg(test)]
mod tests {
    use crate::{
        trace::Trace,
        ui::{
            component::Component,
            geometry::Rect,
            model_tt::{
                component::{Button, Dialog},
                constant,
            },
            component::{Child, FormattedText},
            display,
        },
    };

    use super::*;

    const SCREEN: Rect = constant::screen().inset(theme::borders());

    fn trace(val: &impl Trace) -> String {
        let mut t = Vec::new();
        val.trace(&mut t);
        String::from_utf8(t).unwrap()
    }

    #[test]
    fn trace_example_layout() {
        let mut layout = Dialog::new(
            FormattedText::new::<theme::TTDefaultText>(
                "Testing text layout, with some text, and some more text. And {param}",
            )
            .with(b"param", b"parameters!"),
            Button::with_text(b"Left"),
            Button::with_text(b"Right"),
        );
        layout.place(SCREEN);
        assert_eq!(
            trace(&layout),
            "<Dialog content:<Text content:Testing text layout, with\nsome text, and some more\ntext. And parameters! > left:<Button text:Left > right:<Button text:Right > >",
        )
    }
}
