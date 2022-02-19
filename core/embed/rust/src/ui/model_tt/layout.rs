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
        Button, ButtonMsg, Dialog, DialogMsg, Frame, HoldToConfirm, HoldToConfirmMsg, PinKeyboard,
        PinKeyboardMsg, SwipePage,
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

impl ComponentMsgObj for PinKeyboard {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            PinKeyboardMsg::Cancelled => Ok(CANCELLED.as_obj()),
            PinKeyboardMsg::Confirmed => self.pin().try_into(),
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

        let obj = LayoutObj::new(
            Frame::new(theme::borders(), title, |area| {
                SwipePage::new(
                    area,
                    theme::BG,
                    |area| {
                        let action = action.unwrap_or("".into());
                        let description = description.unwrap_or("".into());
                        let mut para = Paragraphs::new(area);
                        if !reverse {
                            para = para
                                .add::<theme::TTDefaultText>(theme::FONT_BOLD, action)
                                .add::<theme::TTDefaultText>(theme::FONT_NORMAL, description);
                        } else {
                            para = para
                                .add::<theme::TTDefaultText>(theme::FONT_NORMAL, description)
                                .add::<theme::TTDefaultText>(theme::FONT_BOLD, action);
                        }
                        para
                    },
                    |area| {
                        Button::array2(
                            area,
                            |area| Button::with_icon(area, theme::ICON_CANCEL),
                            |msg| (matches!(msg, ButtonMsg::Clicked)).then(|| false),
                            |area| {
                                Button::with_text(area, verb.unwrap_or("CONFIRM".into()))
                                    .styled(theme::button_confirm())
                            },
                            |msg| (matches!(msg, ButtonMsg::Clicked)).then(|| true),
                        )
                    },
                )
            })
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
            component::{Child, FormattedText},
            display,
            model_tt::component::{Button, Dialog},
        },
    };

    use super::*;

    fn trace(val: &impl Trace) -> String {
        let mut t = Vec::new();
        val.trace(&mut t);
        String::from_utf8(t).unwrap()
    }

    #[test]
    fn trace_example_layout() {
        let layout = Child::new(Dialog::new(
            display::screen(),
            |area| {
                FormattedText::new::<theme::TTDefaultText>(
                    area,
                    "Testing text layout, with some text, and some more text. And {param}",
                )
                .with(b"param", b"parameters!")
            },
            |area| Button::with_text(area, b"Left"),
            |area| Button::with_text(area, b"Right"),
        ));
        assert_eq!(
            trace(&layout),
            "<Dialog content:<Text content:Testing text layout, with\nsome text, and some more\ntext. And parameters! > left:<Button text:Left > right:<Button text:Right > >",
        )
    }
}
