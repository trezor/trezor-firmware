use core::convert::{TryFrom, TryInto};

use crate::{
    error::Error,
    micropython::{buffer::Buffer, map::Map, obj::Obj, qstr::Qstr},
    ui::{
        component::{base::ComponentExt, text::paragraphs::Paragraphs, FormattedText},
        layout::obj::LayoutObj,
    },
    util,
};

use super::{
    component::{Button, ButtonMsg, DialogMsg, Frame, HoldToConfirm, HoldToConfirmMsg, SwipePage},
    theme,
};

impl<T> TryFrom<DialogMsg<T, ButtonMsg, ButtonMsg>> for Obj
where
    Obj: TryFrom<T>,
    Error: From<<Obj as TryFrom<T>>::Error>,
{
    type Error = Error;

    fn try_from(val: DialogMsg<T, ButtonMsg, ButtonMsg>) -> Result<Self, Self::Error> {
        match val {
            DialogMsg::Content(c) => Ok(c.try_into()?),
            DialogMsg::Left(ButtonMsg::Clicked) => 1.try_into(),
            DialogMsg::Right(ButtonMsg::Clicked) => 2.try_into(),
            _ => Ok(Obj::const_none()),
        }
    }
}

impl<T> TryFrom<HoldToConfirmMsg<T>> for Obj
where
    Obj: TryFrom<T>,
    Error: From<<Obj as TryFrom<T>>::Error>,
{
    type Error = Error;

    fn try_from(val: HoldToConfirmMsg<T>) -> Result<Self, Self::Error> {
        match val {
            HoldToConfirmMsg::Content(c) => Ok(c.try_into()?),
            HoldToConfirmMsg::Confirmed => 1.try_into(),
            HoldToConfirmMsg::Cancelled => 2.try_into(),
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

#[no_mangle]
extern "C" fn ui_layout_new_confirm_action(
    n_args: usize,
    args: *const Obj,
    kwargs: *const Map,
) -> Obj {
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

#[cfg(test)]
mod tests {
    use crate::{
        trace::Trace,
        ui::{
            component::Component,
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
        let mut layout = Dialog::new(
            FormattedText::new::<theme::TTDefaultText>(
                "Testing text layout, with some text, and some more text. And {param}",
            )
            .with(b"param", b"parameters!"),
            Button::with_text(b"Left"),
            Button::with_text(b"Right"),
        );
        layout.place(display::screen());
        assert_eq!(
            trace(&layout),
            "<Dialog content:<Text content:Testing text layout, with\nsome text, and some more\ntext. And parameters! > left:<Button text:Left > right:<Button text:Right > >",
        )
    }
}
