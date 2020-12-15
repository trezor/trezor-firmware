use core::convert::{TryFrom, TryInto};

use crate::{
    error::Error,
    micropython::{buffer::Buffer, map::Map, obj::Obj, qstr::Qstr},
    ui::{
        component::{Child, Text},
        display,
        layout::obj::LayoutObj,
    },
    util,
};

use super::{
    component::{Button, Dialog, DialogMsg},
    theme,
};

impl<T> TryFrom<DialogMsg<T>> for Obj
where
    Obj: TryFrom<T>,
    Error: From<<T as TryInto<Obj>>::Error>,
{
    type Error = Error;

    fn try_from(val: DialogMsg<T>) -> Result<Self, Self::Error> {
        match val {
            DialogMsg::Content(c) => Ok(c.try_into()?),
            DialogMsg::LeftClicked => 1.try_into(),
            DialogMsg::RightClicked => 2.try_into(),
        }
    }
}

#[no_mangle]
extern "C" fn ui_layout_new_confirm_action(
    n_args: usize,
    args: *const Obj,
    kwargs: *const Map,
) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let title: Option<Buffer> = kwargs.get(Qstr::MP_QSTR_title)?.try_into_option()?;
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

        let obj = LayoutObj::new(Child::new(Dialog::new(
            display::screen(),
            |area| {
                Text::new::<theme::T1DefaultText>(area, format)
                    .with(b"action", action.unwrap_or("".into()))
                    .with(b"description", description.unwrap_or("".into()))
            },
            left,
            right,
            title,
        )))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

#[no_mangle]
extern "C" fn ui_layout_new_confirm_reset(
    n_args: usize,
    args: *const Obj,
    kwargs: *const Map,
) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let prompt: Buffer = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;

        let format = "{bold}{prompt}{normal}\n\rBy continuing you agree\nto {bold}trezor.io/tos";

        let left = |area, pos| Button::with_text(area, pos, "CANCEL", theme::button_cancel());
        let right = |area, pos| Button::with_text(area, pos, "CREATE", theme::button_default());

        let title: Option<Buffer> = None;
        let obj = LayoutObj::new(Child::new(Dialog::new(
            display::screen(),
            |area| Text::new::<theme::T1DefaultText>(area, format).with(b"prompt", prompt),
            Some(left),
            Some(right),
            title,
        )))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

#[no_mangle]
extern "C" fn ui_layout_new_path_warning(
    n_args: usize,
    args: *const Obj,
    kwargs: *const Map,
) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let path: Buffer = kwargs.get(Qstr::MP_QSTR_path)?.try_into()?;
        let title: Buffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;

        //FIXME break path to lines
        let format = "{mono}{path}\n\r{normal}Are you sure?";

        let left = |area, pos| Button::with_text(area, pos, "CANCEL", theme::button_cancel());
        let right = |area, pos| Button::with_text(area, pos, "CONFIRM", theme::button_default());

        let obj = LayoutObj::new(Child::new(Dialog::new(
            display::screen(),
            |area| Text::new::<theme::T1DefaultText>(area, format).with(b"path", path),
            Some(left),
            Some(right),
            Some(title),
        )))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

#[no_mangle]
extern "C" fn ui_layout_new_show_address(
    n_args: usize,
    args: *const Obj,
    kwargs: *const Map,
) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let title: Buffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let address: Buffer = kwargs.get(Qstr::MP_QSTR_address)?.try_into()?;
        let network: Option<Buffer> = kwargs.get(Qstr::MP_QSTR_network)?.try_into_option()?;
        let extra: Option<Buffer> = kwargs.get(Qstr::MP_QSTR_extra)?.try_into_option()?;

        let format = match (&network, &extra) {
            (None, None) => "{mono}{address}",
            (None, _) => "{bold}{extra}\n{mono}{address}",
            (_, None) => "{normal}{network} network\n{mono}{address}",
            (_, _) => "{normal}{network} network\n{bold}{extra}\n{mono}{address}",
        };

        let left = |area, pos| Button::with_text(area, pos, "QR CODE", theme::button_cancel());
        let right = |area, pos| Button::with_text(area, pos, "CONTINUE", theme::button_default());

        let obj = LayoutObj::new(Child::new(Dialog::new(
            display::screen(),
            |area| {
                Text::new::<theme::T1DefaultText>(area, format)
                    .with(b"address", address)
                    .with(b"network", network.unwrap_or("".into()))
                    .with(b"extra", extra.unwrap_or("".into()))
            },
            Some(left),
            Some(right),
            Some(title),
        )))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

#[no_mangle]
extern "C" fn ui_layout_new_show_modal(n_args: usize, args: *const Obj, kwargs: *const Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let title: Option<Buffer> = kwargs.get(Qstr::MP_QSTR_title)?.try_into_option()?;
        let subtitle: Option<Buffer> = kwargs.get(Qstr::MP_QSTR_subtitle)?.try_into_option()?;
        let content: Buffer = kwargs.get(Qstr::MP_QSTR_content)?.try_into()?;
        let button_confirm: Option<Buffer> = kwargs
            .get(Qstr::MP_QSTR_button_confirm)?
            .try_into_option()?;
        let button_cancel: Option<Buffer> =
            kwargs.get(Qstr::MP_QSTR_button_cancel)?.try_into_option()?;

        let format = match &subtitle {
            None => "{content}",
            _ => "{bold}{subtitle}\n\r{normal}{content}",
        };

        let left = button_cancel
            .map(|label| |area, pos| Button::with_text(area, pos, label, theme::button_cancel()));
        let right = button_confirm
            .map(|label| |area, pos| Button::with_text(area, pos, label, theme::button_default()));

        let obj = LayoutObj::new(Child::new(Dialog::new(
            display::screen(),
            |area| {
                Text::new::<theme::T1DefaultText>(area, format)
                    .with(b"content", content)
                    .with(b"subtitle", subtitle.unwrap_or("".into()))
            },
            left,
            right,
            title,
        )))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

#[no_mangle]
extern "C" fn ui_layout_new_confirm_output(
    n_args: usize,
    args: *const Obj,
    kwargs: *const Map,
) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let title: Buffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let subtitle: Option<Buffer> = kwargs.get(Qstr::MP_QSTR_subtitle)?.try_into_option()?;
        let address: Buffer = kwargs.get(Qstr::MP_QSTR_address)?.try_into()?;
        let amount: Buffer = kwargs.get(Qstr::MP_QSTR_amount)?.try_into()?;

        let format = match &subtitle {
            None => "Send {amount} to \n{mono}{address}",
            _ => "{subtitle}\nSend {amount} to \n{mono}{address}",
        };

        let left = |area, pos| Button::with_text(area, pos, "CANCEL", theme::button_cancel());
        let right = |area, pos| Button::with_text(area, pos, "CONFIRM", theme::button_default());

        let obj = LayoutObj::new(Child::new(Dialog::new(
            display::screen(),
            |area| {
                Text::new::<theme::T1DefaultText>(area, format)
                    .with(b"amount", amount)
                    .with(b"address", address)
                    .with(b"subtitle", subtitle.unwrap_or("".into()))
            },
            Some(left),
            Some(right),
            Some(title),
        )))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

#[no_mangle]
extern "C" fn ui_layout_new_confirm_total(
    n_args: usize,
    args: *const Obj,
    kwargs: *const Map,
) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let title: Buffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let label1: Buffer = kwargs.get(Qstr::MP_QSTR_label1)?.try_into()?;
        let amount1: Buffer = kwargs.get(Qstr::MP_QSTR_amount1)?.try_into()?;
        let label2: Buffer = kwargs.get(Qstr::MP_QSTR_label2)?.try_into()?;
        let amount2: Buffer = kwargs.get(Qstr::MP_QSTR_amount2)?.try_into()?;

        let format = "{bold}{label1}\n{mono}{amount1}\n{bold}{label2}\n{mono}{amount2}";

        let left = |area, pos| Button::with_text(area, pos, "X", theme::button_cancel());
        let right =
            |area, pos| Button::with_text(area, pos, "HOLD TO CONFIRM", theme::button_default());

        let obj = LayoutObj::new(Child::new(Dialog::new(
            display::screen(),
            |area| {
                Text::new::<theme::T1DefaultText>(area, format)
                    .with(b"label1", label1)
                    .with(b"amount1", amount1)
                    .with(b"label2", label2)
                    .with(b"amount2", amount2)
            },
            Some(left),
            Some(right),
            Some(title),
        )))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

#[no_mangle]
extern "C" fn ui_layout_new_confirm_metadata(
    n_args: usize,
    args: *const Obj,
    kwargs: *const Map,
) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let title: Buffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let content: Buffer = kwargs.get(Qstr::MP_QSTR_content)?.try_into()?;
        let show_continue: bool = kwargs.get(Qstr::MP_QSTR_show_continue)?.try_into()?;

        let format = if show_continue {
            "{content}\nContinue?"
        } else {
            "{content}"
        };

        let left = |area, pos| Button::with_text(area, pos, "CANCEL", theme::button_cancel());
        let right = |area, pos| Button::with_text(area, pos, "CONFIRM", theme::button_default());

        let obj = LayoutObj::new(Child::new(Dialog::new(
            display::screen(),
            |area| Text::new::<theme::T1DefaultText>(area, format).with(b"content", content),
            Some(left),
            Some(right),
            Some(title),
        )))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

#[no_mangle]
extern "C" fn ui_layout_new_confirm_blob(
    n_args: usize,
    args: *const Obj,
    kwargs: *const Map,
) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let title: Buffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: Option<Buffer> =
            kwargs.get(Qstr::MP_QSTR_description)?.try_into_option()?;
        let data: Buffer = kwargs.get(Qstr::MP_QSTR_data)?.try_into()?;

        let format = if description.is_none() {
            "{mono}{data}"
        } else {
            "{description}\n{mono}{data}"
        };

        let left = |area, pos| Button::with_text(area, pos, "CANCEL", theme::button_cancel());
        let right = |area, pos| Button::with_text(area, pos, "CONFIRM", theme::button_default());

        let obj = LayoutObj::new(Child::new(Dialog::new(
            display::screen(),
            |area| {
                Text::new::<theme::T1DefaultText>(area, format)
                    .with(b"description", description.unwrap_or("".into()))
                    .with(b"data", data)
            },
            Some(left),
            Some(right),
            Some(title),
        )))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

#[no_mangle]
extern "C" fn ui_layout_new_confirm_modify_fee(
    n_args: usize,
    args: *const Obj,
    kwargs: *const Map,
) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let title: Buffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let sign: i32 = kwargs.get(Qstr::MP_QSTR_sign)?.try_into()?;
        let user_fee_change: Buffer = kwargs.get(Qstr::MP_QSTR_user_fee_change)?.try_into()?;
        let total_fee_new: Buffer = kwargs.get(Qstr::MP_QSTR_total_fee_new)?.try_into()?;

        let format = if sign == 0 {
            "Your fee did not change.\n\rTransaction fee:\n{bold}{total_fee_new}"
        } else if sign < 0 {
            "Decrease your fee by:\n{bold}{user_fee_change}\nTransaction fee:\n{bold}{total_fee_new}"
        } else {
            "Increase your fee by:\n{bold}{user_fee_change}\nTransaction fee:\n{bold}{total_fee_new}"
        };

        let left = |area, pos| Button::with_text(area, pos, "X", theme::button_cancel());
        let right =
            |area, pos| Button::with_text(area, pos, "HOLD TO CONFIRM", theme::button_default());

        let obj = LayoutObj::new(Child::new(Dialog::new(
            display::screen(),
            |area| {
                Text::new::<theme::T1DefaultText>(area, format)
                    .with(b"user_fee_change", user_fee_change)
                    .with(b"total_fee_new", total_fee_new)
            },
            Some(left),
            Some(right),
            Some(title),
        )))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

#[no_mangle]
extern "C" fn ui_layout_new_confirm_coinjoin(
    n_args: usize,
    args: *const Obj,
    kwargs: *const Map,
) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let title: Buffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let fee_per_anonymity: Option<Buffer> = kwargs
            .get(Qstr::MP_QSTR_fee_per_anonymity)?
            .try_into_option()?;
        let total_fee: Buffer = kwargs.get(Qstr::MP_QSTR_total_fee)?.try_into()?;

        let format = if fee_per_anonymity.is_none() {
            "Maximum total fees:\n{bold}{total_fee}"
        } else {
            "Fee per anonymity set:\n{bold}{fee_per_anonymity} %\n{normal}Maximum total fees:\n{bold}{total_fee}"
        };

        let left = |area, pos| Button::with_text(area, pos, "X", theme::button_cancel());
        let right =
            |area, pos| Button::with_text(area, pos, "HOLD TO CONFIRM", theme::button_default());

        let obj = LayoutObj::new(Child::new(Dialog::new(
            display::screen(),
            |area| {
                Text::new::<theme::T1DefaultText>(area, format)
                    .with(b"fee_per_anonymity", fee_per_anonymity.unwrap_or("".into()))
                    .with(b"total_fee", total_fee)
            },
            Some(left),
            Some(right),
            Some(title),
        )))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

#[cfg(test)]
mod tests {
    use crate::trace::{Trace, Tracer};

    use super::*;

    impl Tracer for Vec<u8> {
        fn bytes(&mut self, b: &[u8]) {
            self.extend(b)
        }

        fn string(&mut self, s: &str) {
            self.extend(s.as_bytes())
        }

        fn symbol(&mut self, name: &str) {
            self.extend(name.as_bytes())
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
            self.extend(b">")
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
                Text::new::<theme::T1DefaultText>(
                    area,
                    "Testing text layout, with some text, and some more text. And {param}",
                )
                .with(b"param", b"parameters!")
            },
            Some(|area, pos| Button::with_text(area, pos, "Left", theme::button_cancel())),
            Some(|area, pos| Button::with_text(area, pos, "Right", theme::button_default())),
            None,
        ));
        assert_eq!(
            trace(&layout),
            r#"<Dialog content:<Text content:Testing text layout,
with some text, and
some more text. And p-
arameters! > left:<Button text:Left > right:<Button text:Right > >"#
        )
    }
}
