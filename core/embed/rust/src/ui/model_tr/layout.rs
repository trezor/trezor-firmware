use core::{convert::TryInto, ops::Deref};

use heapless::{String, Vec};

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
        Bip39Entry, Bip39EntryMsg, ButtonDetails, ButtonPage, Frame, PassphraseEntry,
        PassphraseEntryMsg, PinEntry, PinEntryMsg, SimpleChoice, SimpleChoiceMsg,
    },
    theme,
};

impl<S, T> ComponentMsgObj for ButtonPage<S, T>
where
    T: Component + Paginate,
    S: AsRef<str>,
    S: Clone,
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

        let verb_cancel = verb_cancel.unwrap_or_default();
        let verb = verb.unwrap_or_default();

        let cancel_btn = if verb_cancel.len() > 0 {
            Some(ButtonDetails::icon(theme::ICON_CANCEL, "cancel".into()).with_cancel())
        } else {
            None
        };

        let mut confirm_btn = if verb.len() > 0 {
            Some(ButtonDetails::new(verb))
        } else {
            None
        };

        // Optional HoldToConfirm
        if hold {
            // TODO: clients might want to set the duration
            confirm_btn = confirm_btn.map(|btn| btn.with_duration(Duration::from_secs(2)));
        }

        // TODO: make sure the text will not be colliding with the buttons
        // - make there some space on the bottom of the text

        let obj = LayoutObj::new(Frame::new(
            title,
            None,
            ButtonPage::new_str_buf(
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
            ButtonPage::new_str(
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
        let share_words_obj: Obj = kwargs.get(Qstr::MP_QSTR_share_words)?;
        let title = "Recovery seed";

        // Parsing the list of share words.
        // Assume there is always just 12 words in the newly generated seed
        // (for now, later we might support SLIP39 with up to 33 words)
        let mut iter_buf = IterBuf::new();
        let iter_words = Iter::try_from_obj_with_buf(share_words_obj, &mut iter_buf)?;
        let mut share_words: Vec<StrBuffer, 12> = Vec::new();
        for word in iter_words {
            share_words.push(word.try_into()?).unwrap();
        }

        let share_words_len = share_words.len() as u8;

        let beginning_text = build_string!(
            40,
            "Write down these ",
            inttostr!(share_words_len),
            " words:\n\n"
        );

        let mut middle_words: String<240> = String::new();
        // Vec<StrBuffer> does not support `enumerate()`
        let mut index: u8 = 0;
        for word in share_words {
            index += 1;
            let line = build_string!(20, inttostr!(index), ". ", word.as_ref(), "\n");

            middle_words.push_str(&line).unwrap();
        }

        let end_text = build_string!(
            40,
            "I wrote down all ",
            inttostr!(share_words_len),
            " words in order."
        );

        // TODO: instead of this could create a new paragraph for the beginning,
        // each word and the end
        let text_to_show = build_string!(
            320,
            beginning_text.as_str(),
            middle_words.as_str(),
            end_text.as_str()
        );

        // Adding hold-to-confirm button at the end
        // Also no possibility of cancelling
        let cancel_btn = None;
        let confirm_btn = Some(ButtonDetails::new("CONFIRM").with_duration(Duration::from_secs(2)));

        let obj = LayoutObj::new(Frame::new(
            title,
            None,
            ButtonPage::new_str(
                Paragraphs::new().add(theme::TEXT_BOLD, text_to_show),
                theme::BG,
            )
            .with_cancel_btn(cancel_btn)
            .with_confirm_btn(confirm_btn),
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn confirm_word(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let choices: Obj = kwargs.get(Qstr::MP_QSTR_choices)?;
        let checked_index: u8 = kwargs.get(Qstr::MP_QSTR_checked_index)?.try_into()?;
        let count: u8 = kwargs.get(Qstr::MP_QSTR_count)?.try_into()?;

        let count_str: String<50> = String::from(count);
        let checked_index_str: String<50> = String::from(checked_index + 1);

        let prompt = build_string!(
            20,
            "Select word ",
            checked_index_str.as_str(),
            "/",
            count_str.as_str()
        );

        // Extracting three words out of choices.
        // TODO: there might be some better way using `map` rather than pushing
        // TODO: this also required to derive `Debug` on StrBuffer - does
        // it take any space in the binary?
        let mut iter_buf = IterBuf::new();
        let iter_words = Iter::try_from_obj_with_buf(choices, &mut iter_buf)?;
        let mut words: Vec<StrBuffer, 3> = Vec::new();
        for word in iter_words {
            words.push(word.try_into()?).unwrap();
        }

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
    ///     share_words: Iterable[str],
    /// ) -> None:
    ///     """Shows a backup seed."""
    Qstr::MP_QSTR_show_share_words => obj_fn_kw!(0, show_share_words).as_obj(),

    /// def confirm_word(
    ///     *,
    ///     choices: Iterable[str],
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
