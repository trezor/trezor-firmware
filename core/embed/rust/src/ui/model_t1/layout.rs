use core::convert::TryInto;

use crate::{
    error::Error,
    micropython::{buffer::Buffer, map::Map, module::Module, obj::Obj, qstr::Qstr},
    ui::{
        component::{
            base::Component,
            paginated::{PageMsg, Paginate},
            text::paragraphs::Paragraphs,
            FormattedText,
        },
        display,
        layout::{
            obj::{ComponentMsgObj, LayoutObj},
            result::{CANCELLED, CONFIRMED},
        },
    },
    util,
};

use super::{
    component::{Button, ButtonPage, Frame},
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

extern "C" fn new_confirm_action(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let title: Buffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let action: Option<Buffer> = kwargs.get(Qstr::MP_QSTR_action)?.try_into_option()?;
        let description: Option<Buffer> =
            kwargs.get(Qstr::MP_QSTR_description)?.try_into_option()?;
        let verb: Option<Buffer> = kwargs.get(Qstr::MP_QSTR_verb)?.try_into_option()?;
        let verb_cancel: Option<Buffer> =
            kwargs.get(Qstr::MP_QSTR_verb_cancel)?.try_into_option()?;
        let reverse: bool = kwargs.get(Qstr::MP_QSTR_reverse)?.try_into()?;

        let format = match (&action, &description, reverse) {
            (Some(_), Some(_), false) => "{bold}{action}\n\r{normal}{description}",
            (Some(_), Some(_), true) => "{normal}{description}\n\r{bold}{action}",
            (Some(_), None, _) => "{bold}{action}",
            (None, Some(_), _) => "{normal}{description}",
            _ => "",
        };

        let left = verb_cancel
            .map(|label| |area, pos| Button::with_text(area, pos, label, theme::button_cancel()));
        let right = verb
            .map(|label| |area, pos| Button::with_text(area, pos, label, theme::button_default()));

        let obj = LayoutObj::new(Frame::new(display::screen(), title, |area| {
            ButtonPage::new(
                area,
                |area| {
                    FormattedText::new::<theme::T1DefaultText>(area, format)
                        .with(b"action", action.unwrap_or("".into()))
                        .with(b"description", description.unwrap_or("".into()))
                },
                theme::BG,
            )
        }))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_text(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let title: Buffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let data: Buffer = kwargs.get(Qstr::MP_QSTR_data)?.try_into()?;
        let description: Option<Buffer> =
            kwargs.get(Qstr::MP_QSTR_description)?.try_into_option()?;

        let obj = LayoutObj::new(Frame::new(display::screen(), title, |area| {
            ButtonPage::new(
                area,
                |area| {
                    Paragraphs::new(area)
                        .add::<theme::T1DefaultText>(
                            theme::FONT_NORMAL,
                            description.unwrap_or("".into()),
                        )
                        .add::<theme::T1DefaultText>(theme::FONT_BOLD, data)
                },
                theme::BG,
            )
        }))?;
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
        ui::model_t1::component::{Dialog, DialogMsg},
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
        U: AsRef<[u8]>,
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
        let layout = Dialog::new(
            display::screen(),
            |area| {
                FormattedText::new::<theme::T1DefaultText>(
                    area,
                    "Testing text layout, with some text, and some more text. And {param}",
                )
                .with(b"param", b"parameters!")
            },
            Some(|area, pos| Button::with_text(area, pos, "Left", theme::button_cancel())),
            Some(|area, pos| Button::with_text(area, pos, "Right", theme::button_default())),
        );
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
        let layout = Frame::new(display::screen(), "Please confirm", |area| {
            Dialog::new(
                area,
                |area| {
                    FormattedText::new::<theme::T1DefaultText>(
                        area,
                        "Testing text layout, with some text, and some more text. And {param}",
                    )
                    .with(b"param", b"parameters!")
                },
                Some(|area, pos| Button::with_text(area, pos, "Left", theme::button_cancel())),
                Some(|area, pos| Button::with_text(area, pos, "Right", theme::button_default())),
            )
        });
        assert_eq!(
            trace(&layout),
            r#"<Frame title:Please confirm content:<Dialog content:<Text content:Testing text layout,
with some text, and
some more text. And p-
arameters! > left:<Button text:Left > right:<Button text:Right > > >"#
        )
    }
}
