use core::convert::TryInto;

use crate::{
    error::Error,
    micropython::{buffer::StrBuffer, map::Map, module::Module, obj::Obj, qstr::Qstr, util},
    ui::{
        component::{
            base::Component,
            paginated::{PageMsg, Paginate},
            text::paragraphs::{Paragraph, Paragraphs},
            FormattedText,
        },
        layout::{
            obj::{ComponentMsgObj, LayoutObj},
            result::{CANCELLED, CONFIRMED},
            util::upy_disable_animation,
        },
    },
};

use super::{
    component::{Button, ButtonPage, ButtonPos, Frame},
    theme,
};

impl<T> ComponentMsgObj for ButtonPage<T>
where
    T: Component + Paginate,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            PageMsg::Content(_) => Err(Error::TypeError),
            PageMsg::Controls(true) => Ok(CONFIRMED.as_obj()),
            PageMsg::Controls(false) => Ok(CANCELLED.as_obj()),
            PageMsg::GoBack => unreachable!(),
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

extern "C" fn new_confirm_action(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let action: Option<StrBuffer> = kwargs.get(Qstr::MP_QSTR_action)?.try_into_option()?;
        let description: Option<StrBuffer> =
            kwargs.get(Qstr::MP_QSTR_description)?.try_into_option()?;
        let verb: Option<StrBuffer> = kwargs.get(Qstr::MP_QSTR_verb)?.try_into_option()?;
        let verb_cancel: Option<StrBuffer> =
            kwargs.get(Qstr::MP_QSTR_verb_cancel)?.try_into_option()?;
        let reverse: bool = kwargs.get(Qstr::MP_QSTR_reverse)?.try_into()?;

        let format = match (&action, &description, reverse) {
            (Some(_), Some(_), false) => "{bold}{action}\n\r{normal}{description}",
            (Some(_), Some(_), true) => "{normal}{description}\n\r{bold}{action}",
            (Some(_), None, _) => "{bold}{action}",
            (None, Some(_), _) => "{normal}{description}",
            _ => "",
        };

        let _left = verb_cancel
            .map(|label| Button::with_text(ButtonPos::Left, label, theme::button_cancel()));
        let _right =
            verb.map(|label| Button::with_text(ButtonPos::Right, label, theme::button_default()));

        let obj = LayoutObj::new(Frame::new(
            title,
            ButtonPage::new(
                FormattedText::new(theme::TEXT_NORMAL, theme::FORMATTED, format)
                    .with("action", action.unwrap_or_default())
                    .with("description", description.unwrap_or_default()),
                theme::BG,
            ),
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_text(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let data: StrBuffer = kwargs.get(Qstr::MP_QSTR_data)?.try_into()?;
        let description: Option<StrBuffer> =
            kwargs.get(Qstr::MP_QSTR_description)?.try_into_option()?;

        let obj = LayoutObj::new(Frame::new(
            title,
            ButtonPage::new(
                Paragraphs::new([
                    Paragraph::new(&theme::TEXT_NORMAL, description.unwrap_or_default()),
                    Paragraph::new(&theme::TEXT_BOLD, data),
                ]),
                theme::BG,
            ),
        ))?;
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

    /// def disable_animation(disable: bool) -> None:
    ///     """Disable animations, debug builds only."""
    Qstr::MP_QSTR_disable_animation => obj_fn_1!(upy_disable_animation).as_obj(),

    /// def confirm_action(
    ///     *,
    ///     title: str,
    ///     action: str | None = None,
    ///     description: str | None = None,
    ///     verb: str | None = None,
    ///     verb_cancel: str | None = None,
    ///     hold: bool = False,
    ///     hold_danger: bool = False,  # unused on TR
    ///     reverse: bool = False,
    /// ) -> object:
    ///     """Confirm action."""
    Qstr::MP_QSTR_confirm_action => obj_fn_kw!(0, new_confirm_action).as_obj(),

    /// def confirm_text(
    ///     *,
    ///     title: str,
    ///     data: str,
    ///     description: str | None,
    /// ) -> object:
    ///     """Confirm text."""
    Qstr::MP_QSTR_confirm_text => obj_fn_kw!(0, new_confirm_text).as_obj(),
};

#[cfg(test)]
mod tests {
    use crate::{
        trace::Trace,
        ui::{
            component::Component,
            model_tr::{
                component::{Dialog, DialogMsg},
                constant,
            },
        },
    };

    use super::*;

    fn trace(val: &impl Trace) -> String {
        let mut t = Vec::new();
        val.trace(&mut t);
        String::from_utf8(t).unwrap()
    }

    impl<T, U> ComponentMsgObj for Dialog<T, U>
    where
        T: ComponentMsgObj,
        U: AsRef<str>,
    {
        fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
            match msg {
                DialogMsg::Content(c) => self.inner().msg_try_into_obj(c),
                DialogMsg::LeftClicked => Ok(CANCELLED.as_obj()),
                DialogMsg::RightClicked => Ok(CONFIRMED.as_obj()),
            }
        }
    }

    #[test]
    fn trace_example_layout() {
        let mut layout = Dialog::new(
            FormattedText::new(
                theme::TEXT_NORMAL,
                theme::FORMATTED,
                "Testing text layout, with some text, and some more text. And {param}",
            )
            .with("param", "parameters!"),
            Some(Button::with_text(
                ButtonPos::Left,
                "Left",
                theme::button_cancel(),
            )),
            Some(Button::with_text(
                ButtonPos::Right,
                "Right",
                theme::button_default(),
            )),
        );
        layout.place(constant::screen());
        assert_eq!(
            trace(&layout),
            r#"<Dialog content:<Text content:Testing text layout,
with some text, and
some more text. And p-
arameters! > left:<Button text:Left > right:<Button text:Right > >"#
        )
    }

    #[test]
    fn trace_layout_title() {
        let mut layout = Frame::new(
            "Please confirm",
            Dialog::new(
                FormattedText::new(
                    theme::TEXT_NORMAL,
                    theme::FORMATTED,
                    "Testing text layout, with some text, and some more text. And {param}",
                )
                .with("param", "parameters!"),
                Some(Button::with_text(
                    ButtonPos::Left,
                    "Left",
                    theme::button_cancel(),
                )),
                Some(Button::with_text(
                    ButtonPos::Right,
                    "Right",
                    theme::button_default(),
                )),
            ),
        );
        layout.place(constant::screen());
        assert_eq!(
            trace(&layout),
            r#"<Frame title:Please confirm content:<Dialog content:<Text content:Testing text layout,
with some text, and
some more text. And p-
arameters! > left:<Button text:Left > right:<Button text:Right > > >"#
        )
    }
}
