use core::convert::{TryFrom, TryInto};

use crate::{
    error::Error,
    micropython::obj::Obj,
    ui::{
        component::{
            model_tt::{ButtonMsg, DialogMsg, FormattedText, HoldToConfirm, HoldToConfirmMsg},
            Child,
        },
        display,
    },
    util,
};

use super::obj::LayoutObj;

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
        let layout = LayoutObj::new(Child::new(HoldToConfirm::new(display::screen(), |area| {
            FormattedText::new(
                area,
                "Testing text layout, with some text, and some more text. And {param}",
            )
            .with(b"param", b"parameters!")
        })))?;
        Ok(layout.into())
    };
    unsafe { util::try_or_raise(block) }
}

#[cfg(test)]
mod tests {
    use crate::{
        trace::{Trace, Tracer},
        ui::component::model_tt::{Button, Dialog},
    };

    use super::*;

    impl Tracer for Vec<u8> {
        fn int(&mut self, i: i64) {
            self.string(&i.to_string());
        }

        fn bytes(&mut self, b: &[u8]) {
            self.extend(b);
        }

        fn string(&mut self, s: &str) {
            self.extend(s.as_bytes());
        }

        fn symbol(&mut self, name: &str) {
            self.extend(name.as_bytes());
        }

        fn open(&mut self, name: &str) {
            self.extend(b"<");
            self.extend(name.as_bytes());
            self.extend(b" ");
        }

        fn field(&mut self, name: &str, value: &dyn Trace) {
            self.extend(name.as_bytes());
            self.extend(b":");
            value.trace(self);
            self.extend(b" ");
        }

        fn close(&mut self) {
            self.extend(b">");
        }
    }

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
                FormattedText::new(
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
            r#"<Dialog content:<Text content:Testing text layout, with
some text, and some more
text. And parameters! > left:<Button text:Left > right:<Button text:Right > >"#
        )
    }
}
