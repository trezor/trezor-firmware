use core::{cmp::Ordering, convert::TryInto, ops::Deref};
use cstr_core::cstr;

use crate::{
    error::Error,
    micropython::{
        buffer::StrBuffer,
        iter::{Iter, IterBuf},
        map::Map,
        module::Module,
        obj::Obj,
        qstr::Qstr,
        util,
    },
    ui::{
        component::{
            base::ComponentExt,
            paginated::{PageMsg, Paginate},
            painter,
            text::paragraphs::{Checklist, Paragraphs},
            Border, Component,
        },
        geometry,
        layout::{
            obj::{ComponentMsgObj, LayoutObj},
            result::{CANCELLED, CONFIRMED, INFO},
        },
    },
};

use super::{
    component::{
        Bip39Input, Button, ButtonMsg, ButtonStyleSheet, CancelConfirmMsg, CancelInfoConfirmMsg,
        Dialog, DialogMsg, Frame, HoldToConfirm, HoldToConfirmMsg, IconDialog, MnemonicInput,
        MnemonicKeyboard, MnemonicKeyboardMsg, NumberInputDialog, NumberInputDialogMsg,
        PassphraseKeyboard, PassphraseKeyboardMsg, PinKeyboard, PinKeyboardMsg, SelectWordMsg,
        Slip39Input, SwipeHoldPage, SwipePage,
    },
    theme,
};

impl TryFrom<CancelConfirmMsg> for Obj {
    type Error = Error;

    fn try_from(value: CancelConfirmMsg) -> Result<Self, Self::Error> {
        match value {
            CancelConfirmMsg::Cancelled => Ok(CANCELLED.as_obj()),
            CancelConfirmMsg::Confirmed => Ok(CONFIRMED.as_obj()),
        }
    }
}

impl TryFrom<CancelInfoConfirmMsg> for Obj {
    type Error = Error;

    fn try_from(value: CancelInfoConfirmMsg) -> Result<Self, Self::Error> {
        match value {
            CancelInfoConfirmMsg::Cancelled => Ok(CANCELLED.as_obj()),
            CancelInfoConfirmMsg::Info => Ok(INFO.as_obj()),
            CancelInfoConfirmMsg::Confirmed => Ok(CONFIRMED.as_obj()),
        }
    }
}

impl TryFrom<SelectWordMsg> for Obj {
    type Error = Error;

    fn try_from(value: SelectWordMsg) -> Result<Self, Self::Error> {
        match value {
            SelectWordMsg::Selected(i) => i.try_into(),
        }
    }
}

impl<T, U> ComponentMsgObj for Dialog<T, U>
where
    T: ComponentMsgObj,
    U: Component,
    <U as Component>::Msg: TryInto<Obj, Error = Error>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            DialogMsg::Content(c) => Ok(self.inner().msg_try_into_obj(c)?),
            DialogMsg::Controls(msg) => msg.try_into(),
        }
    }
}

impl<T, U> ComponentMsgObj for IconDialog<T, U>
where
    T: AsRef<str>,
    U: Component,
    <U as Component>::Msg: TryInto<Obj, Error = Error>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            DialogMsg::Controls(msg) => msg.try_into(),
            _ => unreachable!(),
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

impl<T> ComponentMsgObj for PinKeyboard<T>
where
    T: Deref<Target = str>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            PinKeyboardMsg::Confirmed => self.pin().try_into(),
            PinKeyboardMsg::Cancelled => Ok(CANCELLED.as_obj()),
        }
    }
}

impl ComponentMsgObj for PassphraseKeyboard {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            PassphraseKeyboardMsg::Confirmed => self.passphrase().try_into(),
            PassphraseKeyboardMsg::Cancelled => Ok(CANCELLED.as_obj()),
        }
    }
}

impl<T, U> ComponentMsgObj for MnemonicKeyboard<T, U>
where
    T: MnemonicInput,
    U: Deref<Target = str>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            MnemonicKeyboardMsg::Confirmed => {
                if let Some(word) = self.mnemonic() {
                    word.try_into()
                } else {
                    panic!("invalid mnemonic")
                }
            }
        }
    }
}

impl<T, U> ComponentMsgObj for Frame<T, U>
where
    T: ComponentMsgObj,
    U: AsRef<str>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        self.inner().msg_try_into_obj(msg)
    }
}

impl<T, U> ComponentMsgObj for SwipePage<T, U>
where
    T: Component + Paginate,
    U: Component,
    <U as Component>::Msg: TryInto<Obj, Error = Error>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            PageMsg::Content(_) => Err(Error::TypeError),
            PageMsg::Controls(msg) => msg.try_into(),
        }
    }
}

impl<T> ComponentMsgObj for SwipeHoldPage<T>
where
    T: Component + Paginate,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            PageMsg::Content(_) => Err(Error::TypeError),
            PageMsg::Controls(msg) => msg.try_into(),
        }
    }
}

impl<F> ComponentMsgObj for painter::Painter<F>
where
    F: FnMut(geometry::Rect),
{
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!()
    }
}

impl<T> ComponentMsgObj for Paragraphs<T>
where
    T: AsRef<str>,
{
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!()
    }
}

impl<T> ComponentMsgObj for Checklist<T>
where
    T: AsRef<str>,
{
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!()
    }
}

impl<T, F> ComponentMsgObj for NumberInputDialog<T, F>
where
    T: AsRef<str>,
    F: Fn(u32) -> T,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        let value = self.value().try_into()?;
        match msg {
            NumberInputDialogMsg::Selected => Ok((CONFIRMED.as_obj(), value).try_into()?),
            NumberInputDialogMsg::InfoRequested => Ok((CANCELLED.as_obj(), value).try_into()?),
        }
    }
}

impl<T> ComponentMsgObj for Border<T>
where
    T: ComponentMsgObj,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        self.inner().msg_try_into_obj(msg)
    }
}

extern "C" fn new_confirm_action(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let action: Option<StrBuffer> = kwargs.get(Qstr::MP_QSTR_action)?.try_into_option()?;
        let description: Option<StrBuffer> =
            kwargs.get(Qstr::MP_QSTR_description)?.try_into_option()?;
        let verb: StrBuffer = kwargs.get_or(Qstr::MP_QSTR_verb, "CONFIRM".into())?;
        let verb_cancel: Option<StrBuffer> = kwargs
            .get(Qstr::MP_QSTR_verb_cancel)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let reverse: bool = kwargs.get_or(Qstr::MP_QSTR_reverse, false)?;
        let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;

        let paragraphs = {
            let action = action.unwrap_or_default();
            let description = description.unwrap_or_default();
            let mut paragraphs = Paragraphs::new();
            if !reverse {
                paragraphs = paragraphs
                    .add(theme::TEXT_BOLD, action)
                    .add(theme::TEXT_NORMAL, description);
            } else {
                paragraphs = paragraphs
                    .add(theme::TEXT_NORMAL, description)
                    .add(theme::TEXT_BOLD, action);
            }
            paragraphs
        };

        let obj = if hold {
            LayoutObj::new(
                Frame::new(title, SwipeHoldPage::new(paragraphs, theme::BG)).into_child(),
            )?
        } else {
            let buttons = Button::cancel_confirm_text(verb_cancel, verb);
            LayoutObj::new(
                Frame::new(title, SwipePage::new(paragraphs, buttons, theme::BG)).into_child(),
            )?
        };
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_blob(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let data: StrBuffer = kwargs.get(Qstr::MP_QSTR_data)?.try_into()?;
        let description: StrBuffer =
            kwargs.get_or(Qstr::MP_QSTR_description, StrBuffer::empty())?;
        let extra: StrBuffer = kwargs.get_or(Qstr::MP_QSTR_extra, StrBuffer::empty())?;
        let verb_cancel: Option<StrBuffer> = kwargs
            .get(Qstr::MP_QSTR_verb_cancel)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let _ask_pagination: bool = kwargs.get_or(Qstr::MP_QSTR_ask_pagination, false)?;
        let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;

        let paragraphs = Paragraphs::new()
            .add(theme::TEXT_NORMAL, description)
            .add(theme::TEXT_BOLD, extra)
            .add(theme::TEXT_MONO, data);

        let obj = if hold {
            LayoutObj::new(
                Frame::new(title, SwipeHoldPage::new(paragraphs, theme::BG)).into_child(),
            )?
        } else {
            let buttons = Button::cancel_confirm_text(verb_cancel, "CONFIRM".into());
            LayoutObj::new(
                Frame::new(title, SwipePage::new(paragraphs, buttons, theme::BG)).into_child(),
            )?
        };
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_reset_device(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let prompt: StrBuffer = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let description: StrBuffer = "\nBy continuing you agree to".into();
        let url: StrBuffer = "https://trezor.io/tos".into();

        let paragraphs = Paragraphs::new()
            .add(theme::TEXT_BOLD, prompt)
            .add(theme::TEXT_NORMAL, description)
            .add(theme::TEXT_BOLD, url);

        let buttons = Button::cancel_confirm_text(None, "CONTINUE");
        let obj = LayoutObj::new(
            Frame::new(title, SwipePage::new(paragraphs, buttons, theme::BG)).into_child(),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_qr(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let address: StrBuffer = kwargs.get(Qstr::MP_QSTR_address)?.try_into()?;
        let verb_cancel: StrBuffer = kwargs.get(Qstr::MP_QSTR_verb_cancel)?.try_into()?;
        let case_sensitive: bool = kwargs.get(Qstr::MP_QSTR_case_sensitive)?.try_into()?;

        let buttons = Button::cancel_confirm(
            Button::with_text(verb_cancel),
            Button::with_text("CONFIRM".into()).styled(theme::button_confirm()),
            1,
        );

        let obj = LayoutObj::new(
            Frame::new(
                title,
                Dialog::new(
                    painter::qrcode_painter(address, theme::QR_SIDE_MAX, case_sensitive),
                    buttons,
                ),
            )
            .with_border(theme::borders())
            .into_child(),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_output(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: StrBuffer = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let value: StrBuffer = kwargs.get(Qstr::MP_QSTR_value)?.try_into()?;
        let verb = "NEXT";

        let paragraphs = Paragraphs::new()
            .add(theme::TEXT_NORMAL, description)
            .add(theme::TEXT_MONO, value);

        let buttons = Button::cancel_confirm(
            Button::with_icon(theme::ICON_CANCEL),
            Button::with_text(verb).styled(theme::button_confirm()),
            2,
        );

        let obj = LayoutObj::new(
            Frame::new(title, SwipePage::new(paragraphs, buttons, theme::BG)).into_child(),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_total(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: StrBuffer = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let value: StrBuffer = kwargs.get(Qstr::MP_QSTR_value)?.try_into()?;

        let paragraphs = Paragraphs::new()
            .add(theme::TEXT_NORMAL, description)
            .add(theme::TEXT_MONO, value);

        let obj = LayoutObj::new(
            Frame::new(title, SwipeHoldPage::new(paragraphs, theme::BG)).into_child(),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_joint_total(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let spending_amount: StrBuffer = kwargs.get(Qstr::MP_QSTR_spending_amount)?.try_into()?;
        let total_amount: StrBuffer = kwargs.get(Qstr::MP_QSTR_total_amount)?.try_into()?;

        let paragraphs = Paragraphs::new()
            .add(theme::TEXT_NORMAL, "You are contributing:".into())
            .add(theme::TEXT_MONO, spending_amount)
            .add(theme::TEXT_NORMAL, "To the total amount:".into())
            .add(theme::TEXT_MONO, total_amount);

        let obj = LayoutObj::new(
            Frame::new(
                "JOINT TRANSACTION",
                SwipeHoldPage::new(paragraphs, theme::BG),
            )
            .into_child(),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_modify_output(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let address: StrBuffer = kwargs.get(Qstr::MP_QSTR_address)?.try_into()?;
        let sign: i32 = kwargs.get(Qstr::MP_QSTR_sign)?.try_into()?;
        let amount_change: StrBuffer = kwargs.get(Qstr::MP_QSTR_amount_change)?.try_into()?;
        let amount_new: StrBuffer = kwargs.get(Qstr::MP_QSTR_amount_new)?.try_into()?;

        let description = if sign < 0 {
            "Decrease amount by:"
        } else {
            "Increase amount by:"
        };

        let paragraphs = Paragraphs::new()
            .add(theme::TEXT_NORMAL, "Address:".into())
            .add(theme::TEXT_MONO, address)
            .add_break()
            .add(theme::TEXT_NORMAL, description.into())
            .add(theme::TEXT_MONO, amount_change)
            .add(theme::TEXT_NORMAL, "New amount:".into())
            .add(theme::TEXT_MONO, amount_new);

        let buttons = Button::cancel_confirm(
            Button::with_icon(theme::ICON_CANCEL),
            Button::with_text("NEXT").styled(theme::button_confirm()),
            2,
        );

        let obj = LayoutObj::new(
            Frame::new(
                "MODIFY AMOUNT",
                SwipePage::new(paragraphs, buttons, theme::BG),
            )
            .into_child(),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_modify_fee(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let sign: i32 = kwargs.get(Qstr::MP_QSTR_sign)?.try_into()?;
        let user_fee_change: StrBuffer = kwargs.get(Qstr::MP_QSTR_user_fee_change)?.try_into()?;
        let total_fee_new: StrBuffer = kwargs.get(Qstr::MP_QSTR_total_fee_new)?.try_into()?;

        let (description, change) = match sign {
            s if s < 0 => ("Decrease your fee by:", user_fee_change),
            s if s > 0 => ("Increase your fee by:", user_fee_change),
            _ => ("Your fee did not change.", StrBuffer::empty()),
        };

        let paragraphs = Paragraphs::new()
            .add(theme::TEXT_NORMAL, description.into())
            .add(theme::TEXT_MONO, change)
            .add(theme::TEXT_NORMAL, "\nTransaction fee:".into())
            .add(theme::TEXT_MONO, total_fee_new);

        let buttons = Button::cancel_confirm(
            Button::with_icon(theme::ICON_CANCEL),
            Button::with_text("NEXT").styled(theme::button_confirm()),
            2,
        );

        let obj = LayoutObj::new(
            Frame::new("MODIFY FEE", SwipePage::new(paragraphs, buttons, theme::BG)).into_child(),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

fn new_show_modal(
    kwargs: &Map,
    icon: &'static [u8],
    button_style: ButtonStyleSheet,
) -> Result<Obj, Error> {
    let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
    let description: StrBuffer = kwargs.get_or(Qstr::MP_QSTR_description, StrBuffer::empty())?;
    let button: StrBuffer = kwargs.get(Qstr::MP_QSTR_button)?.try_into()?;
    let allow_cancel: bool = kwargs.get_or(Qstr::MP_QSTR_allow_cancel, true)?;

    let obj = if allow_cancel {
        LayoutObj::new(
            IconDialog::new(
                icon,
                title,
                Button::cancel_confirm(
                    Button::with_icon(theme::ICON_CANCEL).styled(theme::button_cancel()),
                    Button::with_text(button).styled(button_style),
                    2,
                ),
            )
            .with_description(description),
        )?
        .into()
    } else {
        LayoutObj::new(
            IconDialog::new(
                icon,
                title,
                Button::with_text(button).styled(button_style).map(|msg| {
                    (matches!(msg, ButtonMsg::Clicked)).then(|| CancelConfirmMsg::Confirmed)
                }),
            )
            .with_description(description),
        )?
        .into()
    };

    Ok(obj)
}

extern "C" fn new_show_error(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        new_show_modal(kwargs, theme::IMAGE_ERROR, theme::button_default())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_warning(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        new_show_modal(kwargs, theme::IMAGE_WARN, theme::button_reset())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_success(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        new_show_modal(kwargs, theme::IMAGE_SUCCESS, theme::button_confirm())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_info(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        new_show_modal(kwargs, theme::IMAGE_INFO, theme::button_info())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_simple(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: Option<StrBuffer> = kwargs.get(Qstr::MP_QSTR_title)?.try_into_option()?;
        let description: StrBuffer =
            kwargs.get_or(Qstr::MP_QSTR_description, StrBuffer::empty())?;
        let button: StrBuffer = kwargs.get(Qstr::MP_QSTR_button)?.try_into()?;

        let obj = if let Some(t) = title {
            LayoutObj::new(Frame::new(
                t,
                Dialog::new(
                    Paragraphs::new().add(theme::TEXT_NORMAL, description),
                    Button::with_text(button).map(|msg| {
                        (matches!(msg, ButtonMsg::Clicked)).then(|| CancelConfirmMsg::Confirmed)
                    }),
                ),
            ))?
            .into()
        } else {
            LayoutObj::new(Border::new(
                theme::borders(),
                Dialog::new(
                    Paragraphs::new().add(theme::TEXT_NORMAL, description),
                    Button::with_text(button).map(|msg| {
                        (matches!(msg, ButtonMsg::Clicked)).then(|| CancelConfirmMsg::Confirmed)
                    }),
                ),
            ))?
            .into()
        };

        Ok(obj)
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_payment_request(
    n_args: usize,
    args: *const Obj,
    kwargs: *mut Map,
) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let description: StrBuffer = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let memos: Obj = kwargs.get(Qstr::MP_QSTR_memos)?;

        let mut paragraphs = Paragraphs::new().add(theme::TEXT_NORMAL, description);

        let mut iter_buf = IterBuf::new();
        let iter = Iter::try_from_obj_with_buf(memos, &mut iter_buf)?;
        for memo in iter {
            let text: StrBuffer = memo.try_into()?;
            paragraphs = paragraphs.add(theme::TEXT_NORMAL, text);
        }

        let buttons = Button::cancel_info_confirm("CONFIRM", "DETAILS");

        let obj = LayoutObj::new(
            Frame::new(
                "SENDING",
                SwipePage::new(paragraphs, buttons, theme::BG).with_button_rows(2),
            )
            .into_child(),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_coinjoin(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let coin_name: StrBuffer = kwargs.get(Qstr::MP_QSTR_coin_name)?.try_into()?;
        let max_rounds: StrBuffer = kwargs.get(Qstr::MP_QSTR_max_rounds)?.try_into()?;
        let max_feerate: StrBuffer = kwargs.get(Qstr::MP_QSTR_max_feerate)?.try_into()?;

        let paragraphs = Paragraphs::new()
            .add(theme::TEXT_NORMAL, "Coin name:".into())
            .add(theme::TEXT_BOLD, coin_name)
            .add(theme::TEXT_NORMAL, "Maximum rounds:".into())
            .add(theme::TEXT_BOLD, max_rounds)
            .add(theme::TEXT_NORMAL, "Maximum mining fee:".into())
            .add(theme::TEXT_BOLD, max_feerate);

        let obj = LayoutObj::new(
            Frame::new(
                "AUTHORIZE COINJOIN",
                SwipeHoldPage::new(paragraphs, theme::BG),
            )
            .into_child(),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_pin(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let prompt: StrBuffer = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let subprompt: StrBuffer = kwargs.get(Qstr::MP_QSTR_subprompt)?.try_into()?;
        let allow_cancel: bool = kwargs.get_or(Qstr::MP_QSTR_allow_cancel, true)?;
        let warning: Option<StrBuffer> = kwargs.get(Qstr::MP_QSTR_warning)?.try_into_option()?;
        let obj = LayoutObj::new(
            PinKeyboard::new(prompt, subprompt, warning, allow_cancel).into_child(),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_passphrase(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let _prompt: StrBuffer = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let _max_len: u32 = kwargs.get(Qstr::MP_QSTR_max_len)?.try_into()?;
        let obj = LayoutObj::new(PassphraseKeyboard::new().into_child())?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_bip39(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let prompt: StrBuffer = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let obj = LayoutObj::new(MnemonicKeyboard::new(Bip39Input::new(), prompt).into_child())?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_slip39(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let prompt: StrBuffer = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let obj = LayoutObj::new(MnemonicKeyboard::new(Slip39Input::new(), prompt).into_child())?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_select_word(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: StrBuffer = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let words_iterable: Obj = kwargs.get(Qstr::MP_QSTR_words)?;

        let mut words = [StrBuffer::empty(), StrBuffer::empty(), StrBuffer::empty()];
        let mut iter_buf = IterBuf::new();
        let mut iter = Iter::try_from_obj_with_buf(words_iterable, &mut iter_buf)?;
        let words_err = || Error::ValueError(cstr!("Invalid words count"));
        for item in &mut words {
            *item = iter.next().ok_or_else(words_err)?.try_into()?;
        }
        if iter.next().is_some() {
            return Err(words_err());
        }

        let paragraphs = Paragraphs::new().add(theme::TEXT_NORMAL, description);
        let buttons = Button::select_word(words);

        let obj = LayoutObj::new(
            Frame::new(
                title,
                SwipePage::new(paragraphs, buttons, theme::BG).with_button_rows(3),
            )
            .into_child(),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_share_words(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let pages: Obj = kwargs.get(Qstr::MP_QSTR_pages)?;

        let mut paragraphs = Paragraphs::new();
        let mut iter_buf = IterBuf::new();
        let iter = Iter::try_from_obj_with_buf(pages, &mut iter_buf)?;
        for page in iter {
            let text: StrBuffer = page.try_into()?;
            paragraphs = paragraphs.add(theme::TEXT_MONO, text).add_break();
        }

        let obj = LayoutObj::new(
            Frame::new(title, SwipeHoldPage::without_cancel(paragraphs, theme::BG)).into_child(),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_number(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let min_count: u32 = kwargs.get(Qstr::MP_QSTR_min_count)?.try_into()?;
        let max_count: u32 = kwargs.get(Qstr::MP_QSTR_max_count)?.try_into()?;
        let count: u32 = kwargs.get(Qstr::MP_QSTR_count)?.try_into()?;
        let description_callback: Obj = kwargs.get(Qstr::MP_QSTR_description)?;

        let callback = move |i: u32| {
            StrBuffer::try_from(
                description_callback
                    .call_with_n_args(&[i.try_into().unwrap()])
                    .unwrap(),
            )
            .unwrap()
        };

        let obj = LayoutObj::new(
            Frame::new(
                title,
                NumberInputDialog::new(min_count, max_count, count, callback),
            )
            .with_border(theme::borders())
            .into_child(),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_checklist(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let button: StrBuffer = kwargs.get(Qstr::MP_QSTR_button)?.try_into()?;
        let active: usize = kwargs.get(Qstr::MP_QSTR_active)?.try_into()?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;

        let mut iter_buf = IterBuf::new();
        let mut paragraphs = Paragraphs::new().with_spacing(theme::CHECKLIST_SPACING);
        let iter = Iter::try_from_obj_with_buf(items, &mut iter_buf)?;
        for (i, item) in iter.enumerate() {
            let color = match i.cmp(&active) {
                Ordering::Less => theme::GREEN_DARK,
                Ordering::Equal => theme::FG,
                Ordering::Greater => theme::GREY_LIGHT,
            };
            let text: StrBuffer = item.try_into()?;
            paragraphs = paragraphs.add_color(theme::TEXT_NORMAL, color, text);
        }

        let obj = LayoutObj::new(
            Frame::new(
                title,
                Dialog::new(
                    Checklist::from_paragraphs(
                        theme::ICON_LIST_CURRENT,
                        theme::ICON_LIST_CHECK,
                        active,
                        paragraphs,
                    ),
                    Button::with_text(button).map(|msg| {
                        (matches!(msg, ButtonMsg::Clicked)).then(|| CancelConfirmMsg::Confirmed)
                    }),
                ),
            )
            .with_border(theme::borders())
            .into_child(),
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

    /// INFO: object
    Qstr::MP_QSTR_INFO => INFO.as_obj(),

    /// def confirm_action(
    ///     *,
    ///     title: str,
    ///     action: str | None = None,
    ///     description: str | None = None,
    ///     verb: str | None = None,
    ///     verb_cancel: str | None = None,
    ///     hold: bool = False,
    ///     reverse: bool = False,
    /// ) -> object:
    ///     """Confirm action."""
    Qstr::MP_QSTR_confirm_action => obj_fn_kw!(0, new_confirm_action).as_obj(),

    /// def confirm_blob(
    ///     *,
    ///     title: str,
    ///     data: str,
    ///     description: str = "",
    ///     extra: str = "",
    ///     verb_cancel: str | None = None,
    ///     ask_pagination: bool = False,
    ///     hold: bool = False,
    /// ) -> object:
    ///     """Confirm byte sequence data."""
    Qstr::MP_QSTR_confirm_blob => obj_fn_kw!(0, new_confirm_blob).as_obj(),

    /// def confirm_reset_device(
    ///     *,
    ///     title: str,
    ///     prompt: str,
    /// ) -> object:
    ///     """Confirm TOS before device setup."""
    Qstr::MP_QSTR_confirm_reset_device => obj_fn_kw!(0, new_confirm_reset_device).as_obj(),

    /// def show_qr(
    ///     *,
    ///     title: str,
    ///     address: str,
    ///     verb_cancel: str,
    ///     case_sensitive: bool,
    /// ) -> object:
    ///     """Show QR code."""
    Qstr::MP_QSTR_show_qr => obj_fn_kw!(0, new_show_qr).as_obj(),

    /// def confirm_output(
    ///     *,
    ///     title: str,
    ///     description: str,
    ///     value: str,
    ///     verb: str = "NEXT",
    /// ) -> object:
    ///     """Confirm output."""
    Qstr::MP_QSTR_confirm_output => obj_fn_kw!(0, new_confirm_output).as_obj(),

    /// def confirm_total(
    ///     *,
    ///     title: str,
    ///     description: str,
    ///     value: str,
    /// ) -> object:
    ///     """Confirm total."""
    Qstr::MP_QSTR_confirm_total => obj_fn_kw!(0, new_confirm_total).as_obj(),

    /// def confirm_joint_total(
    ///     *,
    ///     spending_amount: str,
    ///     total_amount: str,
    /// ) -> object:
    ///     """Confirm total if there are external inputs."""
    Qstr::MP_QSTR_confirm_joint_total => obj_fn_kw!(0, new_confirm_joint_total).as_obj(),

    /// def confirm_modify_output(
    ///     *,
    ///     address: str,
    ///     sign: int,
    ///     amount_change: str,
    ///     amount_new: str,
    /// ) -> object:
    ///     """Decrease or increase amount for given address."""
    Qstr::MP_QSTR_confirm_modify_output => obj_fn_kw!(0, new_confirm_modify_output).as_obj(),

    /// def confirm_modify_fee(
    ///     *,
    ///     sign: int,
    ///     user_fee_change: str,
    ///     total_fee_new: str,
    /// ) -> object:
    ///     """Decrease or increase transaction fee."""
    Qstr::MP_QSTR_confirm_modify_fee => obj_fn_kw!(0, new_confirm_modify_fee).as_obj(),

    /// def show_error(
    ///     *,
    ///     title: str,
    ///     button: str,
    ///     description: str = "",
    ///     allow_cancel: bool = False,
    /// ) -> object:
    ///     """Error modal."""
    Qstr::MP_QSTR_show_error => obj_fn_kw!(0, new_show_error).as_obj(),

    /// def show_warning(
    ///     *,
    ///     title: str,
    ///     button: str,
    ///     description: str = "",
    ///     allow_cancel: bool = False,
    /// ) -> object:
    ///     """Warning modal."""
    Qstr::MP_QSTR_show_warning => obj_fn_kw!(0, new_show_warning).as_obj(),

    /// def show_success(
    ///     *,
    ///     title: str,
    ///     button: str,
    ///     description: str = "",
    ///     allow_cancel: bool = False,
    /// ) -> object:
    ///     """Success modal."""
    Qstr::MP_QSTR_show_success => obj_fn_kw!(0, new_show_success).as_obj(),

    /// def show_info(
    ///     *,
    ///     title: str,
    ///     button: str,
    ///     description: str = "",
    ///     allow_cancel: bool = False,
    /// ) -> object:
    ///     """Info modal."""
    Qstr::MP_QSTR_show_info => obj_fn_kw!(0, new_show_info).as_obj(),

    /// def show_simple(
    ///     *,
    ///     title: str | None,
    ///     description: str,
    ///     button: str,
    /// ) -> object:
    ///     """Simple dialog with text and one button."""
    Qstr::MP_QSTR_show_simple => obj_fn_kw!(0, new_show_simple).as_obj(),

    /// def confirm_payment_request(
    ///     *,
    ///     description: str,
    ///     memos: Iterable[str],
    /// ) -> object:
    ///     """Confirm payment request."""
    Qstr::MP_QSTR_confirm_payment_request => obj_fn_kw!(0, new_confirm_payment_request).as_obj(),

    /// def confirm_coinjoin(
    ///     *,
    ///     coin_name: str,
    ///     max_rounds: str,
    ///     max_feerate: str,
    /// ) -> object:
    ///     """Confirm coinjoin authorization."""
    Qstr::MP_QSTR_confirm_coinjoin => obj_fn_kw!(0, new_confirm_coinjoin).as_obj(),

    /// def request_pin(
    ///     *,
    ///     prompt: str,
    ///     subprompt: str,
    ///     allow_cancel: bool = True,
    ///     warning: str | None = None,
    /// ) -> str | object:
    ///     """Request pin on device."""
    Qstr::MP_QSTR_request_pin => obj_fn_kw!(0, new_request_pin).as_obj(),

    /// def request_passphrase(
    ///     *,
    ///     prompt: str,
    ///     max_len: int,
    /// ) -> str | object:
    ///    """Passphrase input keyboard."""
    Qstr::MP_QSTR_request_passphrase => obj_fn_kw!(0, new_request_passphrase).as_obj(),

    /// def request_bip39(
    ///     *,
    ///     prompt: str,
    /// ) -> str:
    ///    """BIP39 word input keyboard."""
    Qstr::MP_QSTR_request_bip39 => obj_fn_kw!(0, new_request_bip39).as_obj(),

    /// def request_slip39(
    ///     *,
    ///     prompt: str,
    /// ) -> str:
    ///    """SLIP39 word input keyboard."""
    Qstr::MP_QSTR_request_slip39 => obj_fn_kw!(0, new_request_slip39).as_obj(),

    /// def select_word(
    ///     *,
    ///     title: str,
    ///     description: str,
    ///     words: Iterable[str],
    /// ) -> int:
    ///    """Select mnemonic word from three possibilities - seed check after backup. The
    ///    iterable must be of exact size. Returns index in range `0..3`."""
    Qstr::MP_QSTR_select_word => obj_fn_kw!(0, new_select_word).as_obj(),

    /// def show_share_words(
    ///     *,
    ///     title: str,
    ///     pages: Iterable[str],
    /// ) -> object:
    ///    """Show mnemonic for backup. Expects the words pre-divided into individual pages."""
    Qstr::MP_QSTR_show_share_words => obj_fn_kw!(0, new_show_share_words).as_obj(),

    /// def request_number(
    ///     *,
    ///     title: str,
    ///     count: int,
    ///     min_count: int,
    ///     max_count: int,
    ///     description: Callable[[int], str],
    /// ) -> object:
    ///    """Number input with + and - buttons, description, and info button."""
    Qstr::MP_QSTR_request_number => obj_fn_kw!(0, new_request_number).as_obj(),

    /// def show_checklist(
    ///     *,
    ///     title: str,
    ///     items: Iterable[str],
    ///     active: int,
    ///     button: str,
    /// ) -> object:
    ///    """Checklist of backup steps. Active index is highlighted, previous items have check
    ///    mark nex to them."""
    Qstr::MP_QSTR_show_checklist => obj_fn_kw!(0, new_show_checklist).as_obj(),
};

#[cfg(test)]
mod tests {
    use crate::{
        trace::Trace,
        ui::{
            component::{Component, FormattedText},
            geometry::Rect,
            model_tt::constant,
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
        let buttons =
            Button::cancel_confirm(Button::with_text("Left"), Button::with_text("Right"), 1);
        let mut layout = Dialog::new(
            FormattedText::new(
                theme::TEXT_NORMAL,
                theme::FORMATTED,
                "Testing text layout, with some text, and some more text. And {param}",
            )
            .with("param", "parameters!"),
            buttons,
        );
        layout.place(SCREEN);
        assert_eq!(
            trace(&layout),
            "<Dialog content:<Text content:Testing text layout, with\nsome text, and some more\ntext. And parameters! > controls:<Tuple 0:<GridPlaced inner:<Button text:Left > > 1:<GridPlaced inner:<Button text:Right > > > >",
        )
    }
}
