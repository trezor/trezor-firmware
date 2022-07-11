use core::{convert::TryInto, ops::Deref};

use heapless::{String, Vec};

use crate::{
    error::Error,
    micropython::{buffer::StrBuffer, map::Map, module::Module, obj::Obj, qstr::Qstr, util},
    time::Duration,
    ui::{
        component::{
            base::{Component, ComponentExt},
            paginated::{PageMsg, Paginate},
            text::paragraphs::Paragraphs,
            FormattedText,
        },
        layout::{
            obj::{ComponentMsgObj, LayoutObj},
            result::{CANCELLED, CONFIRMED, INFO},
        },
    },
};

use super::{
    component::{
        Bip39Entry, Bip39EntryMsg, Button, ButtonDetails, ButtonPage, ButtonPos, Frame,
        PassphraseEntry, PassphraseEntryMsg, PinEntry, PinEntryMsg, SimpleChoice, SimpleChoiceMsg,
    },
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

impl ComponentMsgObj for PinEntry {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            PinEntryMsg::Confirmed => self.pin().try_into(),
            PinEntryMsg::Cancelled => Ok(CANCELLED.as_obj()),
        }
    }
}

impl<T, const N: usize> ComponentMsgObj for SimpleChoice<T, N>
where
    T: Deref<Target = str>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            SimpleChoiceMsg::Result(choice) => choice.as_str().try_into(),
        }
    }
}

impl ComponentMsgObj for Bip39Entry {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            Bip39EntryMsg::ResultWord(word) => word.as_str().try_into(),
        }
    }
}

impl ComponentMsgObj for PassphraseEntry {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            PassphraseEntryMsg::Confirmed => self.passphrase().try_into(),
            PassphraseEntryMsg::Cancelled => Ok(CANCELLED.as_obj()),
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
        let hold: bool = kwargs.get(Qstr::MP_QSTR_hold)?.try_into()?;

        let format = match (&action, &description, reverse) {
            (Some(_), Some(_), false) => "{bold}{action}\n\r{normal}{description}",
            (Some(_), Some(_), true) => "{normal}{description}\n\r{bold}{action}",
            (Some(_), None, _) => "{bold}{action}",
            (None, Some(_), _) => "{normal}{description}",
            _ => "",
        };

        // TODO: use verb and verb_cancel

        let cancel_btn = ButtonDetails::cancel("CANCEL");
        let mut confirm_btn = ButtonDetails::new("CONFIRM");
        if hold {
            confirm_btn = confirm_btn.with_duration(Duration::from_secs(2));
        }

        let _left = verb_cancel
            .map(|label| Button::with_text(ButtonPos::Left, label, theme::button_cancel()));
        let _right =
            verb.map(|label| Button::with_text(ButtonPos::Right, label, theme::button_default()));

        let obj = LayoutObj::new(Frame::new(
            title,
            None,
            ButtonPage::new(
                FormattedText::new(theme::TEXT_NORMAL, theme::FORMATTED, format)
                    .with("action", action.unwrap_or_default())
                    .with("description", description.unwrap_or_default()),
                theme::BG,
            )
            .with_cancel_btn(cancel_btn)
            .with_confirm_btn(confirm_btn),
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
            None,
            ButtonPage::new(
                Paragraphs::new()
                    .add(theme::TEXT_NORMAL, description.unwrap_or_default())
                    .add(theme::TEXT_BOLD, data),
                theme::BG,
            ),
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn request_pin(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let prompt: StrBuffer = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let _subprompt: StrBuffer = kwargs.get(Qstr::MP_QSTR_subprompt)?.try_into()?;
        let _allow_cancel: Option<bool> =
            kwargs.get(Qstr::MP_QSTR_allow_cancel)?.try_into_option()?;

        let obj = LayoutObj::new(PinEntry::new(prompt).into_child())?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn show_share_words(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let share_words: StrBuffer = kwargs.get(Qstr::MP_QSTR_share_words)?.try_into()?;
        let title = "Recovery seed";

        let share_words_len = share_words.split(',').count();
        let share_words_len_str: String<10> = String::from(share_words_len as i16);

        let beginning_text = build_string!(
            50,
            "Write down these ",
            share_words_len_str.as_str(),
            " words:\n\n"
        );

        let mut middle_words: String<500> = String::new();
        for (index, word) in share_words.split(',').enumerate() {
            let line = build_string!(
                50,
                String::<2>::from(index as i16 + 1).as_str(),
                ". ",
                word,
                "\n\n\n"
            );

            middle_words.push_str(&line).unwrap();
        }

        let end_text = build_string!(
            50,
            "I wrote down all ",
            share_words_len_str.as_str(),
            " words in order."
        );

        let text_to_show = build_string!(
            600,
            beginning_text.as_str(),
            middle_words.as_str(),
            end_text.as_str()
        );

        let obj = LayoutObj::new(Frame::new(
            title,
            None,
            ButtonPage::new(
                Paragraphs::new().add(theme::TEXT_BOLD, text_to_show),
                theme::BG,
            ),
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn confirm_word(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let choices: StrBuffer = kwargs.get(Qstr::MP_QSTR_choices)?.try_into()?;
        let checked_index: u8 = kwargs.get(Qstr::MP_QSTR_checked_index)?.try_into()?;
        let count: u8 = kwargs.get(Qstr::MP_QSTR_count)?.try_into()?;

        let count_str: String<50> = String::from(count);
        let checked_index_str: String<50> = String::from(checked_index + 1);

        let prompt = build_string!(
            50,
            "Select word ",
            checked_index_str.as_str(),
            " of ",
            count_str.as_str(),
            ":"
        );

        let words: Vec<String<50>, 24> = choices.split(',').map(String::from).collect();

        let obj = LayoutObj::new(Frame::new(
            prompt,
            None,
            SimpleChoice::new(words).into_child(),
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn request_word_count(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let text: StrBuffer = kwargs.get(Qstr::MP_QSTR_text)?.try_into()?;

        let choices: Vec<&str, 5> = ["12", "18", "20", "24", "33"].into_iter().collect();

        let obj = LayoutObj::new(Frame::new(
            title,
            Some(text),
            SimpleChoice::new(choices).into_child(),
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn request_word_bip39(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let prompt: StrBuffer = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;

        let obj = LayoutObj::new(Frame::new(prompt, None, Bip39Entry::new().into_child()))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn request_passphrase(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let prompt: StrBuffer = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let _max_len: u8 = kwargs.get(Qstr::MP_QSTR_max_len)?.try_into()?;

        let obj = LayoutObj::new(Frame::new(
            prompt,
            None,
            PassphraseEntry::new().into_child(),
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

    /// def request_pin(
    ///     *,
    ///     prompt: str,
    ///     subprompt: str | None = None,
    ///     allow_cancel: bool | None = None,
    /// ) -> str | object:
    ///     """Request pin on device."""
    Qstr::MP_QSTR_request_pin => obj_fn_kw!(0, request_pin).as_obj(),

    /// def confirm_text(
    ///     *,
    ///     title: str,
    ///     data: str,
    ///     description: str | None,
    /// ) -> object:
    ///     """Confirm text."""
    Qstr::MP_QSTR_confirm_text => obj_fn_kw!(0, new_confirm_text).as_obj(),

    /// def show_share_words(
    ///     *,
    ///     share_words: str,  # words delimited by "," ... TODO: support list[str]
    /// ) -> None:
    ///     """Shows a backup seed."""
    Qstr::MP_QSTR_show_share_words => obj_fn_kw!(0, show_share_words).as_obj(),

    /// def confirm_word(
    ///     *,
    ///     choices: str,  # words delimited by "," ... TODO: support list[str]
    ///     checked_index: int,
    ///     count: int,
    ///     share_index: int | None,
    ///     group_index: int | None,
    /// ) -> None:
    ///     """Shows a backup seed."""
    Qstr::MP_QSTR_confirm_word => obj_fn_kw!(0, confirm_word).as_obj(),

    /// def request_word_count(
    ///     *,
    ///     title: str,
    ///     text: str,
    /// ) -> str:  # TODO: make it return int
    ///     """Get word count for recovery."""
    Qstr::MP_QSTR_request_word_count => obj_fn_kw!(0, request_word_count).as_obj(),

    /// def request_word_bip39(
    ///     *,
    ///     prompt: str,
    /// ) -> str:
    ///     """Get recovery word for BIP39."""
    Qstr::MP_QSTR_request_word_bip39 => obj_fn_kw!(0, request_word_bip39).as_obj(),

    /// def request_passphrase(
    ///     *,
    ///     prompt: str,
    ///     max_len: int,
    /// ) -> str:
    ///     """Get passphrase."""
    Qstr::MP_QSTR_request_passphrase => obj_fn_kw!(0, request_passphrase).as_obj(),
};

#[cfg(test)]
mod tests {
    //     use crate::{
    //         trace::Trace,
    //         ui::{
    //             component::Component,
    //             model_tr::{
    //                 component::{Dialog, DialogMsg},
    //                 constant,
    //             },
    //         },
    //     };

    //     use super::*;

    //     fn trace(val: &impl Trace) -> String {
    //         let mut t = Vec::new();
    //         val.trace(&mut t);
    //         String::from_utf8(t).unwrap()
    //     }

    //     impl<T, U> ComponentMsgObj for Dialog<T, U>
    //     where
    //         T: ComponentMsgObj,
    //         U: AsRef<str>,
    //     {
    //         fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error>
    // {             match msg {
    //                 DialogMsg::Content(c) =>
    // self.inner().msg_try_into_obj(c),                 
    // DialogMsg::LeftClicked => Ok(CANCELLED.as_obj()),                 
    // DialogMsg::RightClicked => Ok(CONFIRMED.as_obj()),             }
    //         }
    //     }

    //     #[test]
    //     fn trace_example_layout() {
    //         let mut layout = Dialog::new(
    //             FormattedText::new(
    //                 theme::TEXT_NORMAL,
    //                 theme::FORMATTED,
    //                 "Testing text layout, with some text, and some more text.
    // And {param}",             )
    //             .with("param", "parameters!"),
    //             Some(Button::with_text(
    //                 ButtonPos::Left,
    //                 "Left",
    //                 theme::button_cancel(),
    //             )),
    //             Some(Button::with_text(
    //                 ButtonPos::Right,
    //                 "Right",
    //                 theme::button_default(),
    //             )),
    //         );
    //         layout.place(constant::screen());
    //         assert_eq!(
    //             trace(&layout),
    //             r#"<Dialog content:<Text content:Testing text layout,
    // with some text, and
    // some more text. And p-
    // arameters! > left:<Button text:Left > right:<Button text:Right > >"#
    //         )
    //     }

    //     #[test]
    //     fn trace_layout_title() {
    //         let mut layout = Frame::new(
    //             "Please confirm",
    //             Dialog::new(
    //                 FormattedText::new(
    //                     theme::TEXT_NORMAL,
    //                     theme::FORMATTED,
    //                     "Testing text layout, with some text, and some more
    // text. And {param}",                 )
    //                 .with("param", "parameters!"),
    //                 Some(Button::with_text(
    //                     ButtonPos::Left,
    //                     "Left",
    //                     theme::button_cancel(),
    //                 )),
    //                 Some(Button::with_text(
    //                     ButtonPos::Right,
    //                     "Right",
    //                     theme::button_default(),
    //                 )),
    //             ),
    //         );
    //         layout.place(constant::screen());
    //         assert_eq!(
    //             trace(&layout),
    //             r#"<Frame title:Please confirm content:<Dialog content:<Text
    // content:Testing text layout, with some text, and
    // some more text. And p-
    // arameters! > left:<Button text:Left > right:<Button text:Right > > >"#
    //         )
    //     }
}
