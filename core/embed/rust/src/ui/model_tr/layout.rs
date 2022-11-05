use core::convert::TryInto;

use heapless::Vec;

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
            text::paragraphs::{Paragraph, ParagraphSource, ParagraphVecLong, Paragraphs, VecExt},
            FormattedText,
        },
        display::Font,
        layout::{
            obj::{ComponentMsgObj, LayoutObj},
            result::{CANCELLED, CONFIRMED, INFO},
            util::{iter_into_objs, iter_into_vec},
        },
        model_tr::component::LineAlignment,
    },
};

use super::{
    component::{
        Bip39Entry, Bip39EntryMsg, ButtonActions, ButtonDetails, ButtonLayout, ButtonPage, Flow,
        FlowMsg, FlowPages, Frame, Page, PassphraseEntry, PassphraseEntryMsg, PinEntry,
        PinEntryMsg, ShareWords, SimpleChoice, SimpleChoiceMsg,
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

impl<F, const M: usize> ComponentMsgObj for Flow<F, M>
where
    F: Fn(u8) -> Page<M>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            FlowMsg::Confirmed => Ok(CONFIRMED.as_obj()),
            FlowMsg::Cancelled => Ok(CANCELLED.as_obj()),
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
    T: AsRef<str>,
    T: Clone,
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

        // TODO: could be replaced by Flow with one element after it supports pagination

        let format = match (&action, &description, reverse) {
            (Some(_), Some(_), false) => "{Font::bold}{action}\n\r{Font::normal}{description}",
            (Some(_), Some(_), true) => "{Font::normal}{description}\n\r{Font::bold}{action}",
            (Some(_), None, _) => "{Font::bold}{action}",
            (None, Some(_), _) => "{Font::normal}{description}",
            _ => "",
        };

        let verb_cancel = verb_cancel.unwrap_or_default();
        let verb = verb.unwrap_or_default();

        let cancel_btn = if verb_cancel.len() > 0 {
            Some(ButtonDetails::cancel_icon())
        } else {
            None
        };

        let mut confirm_btn = if verb.len() > 0 {
            Some(ButtonDetails::text(verb))
        } else {
            None
        };

        // Optional HoldToConfirm
        if hold {
            // TODO: clients might want to set the duration
            confirm_btn = confirm_btn.map(|btn| btn.with_duration(Duration::from_secs(2)));
        }

        let obj = LayoutObj::new(Frame::new(
            title,
            ButtonPage::new_str_buf(
                FormattedText::new(theme::TEXT_MONO, theme::FORMATTED, format)
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

        // TODO: could be replaced by Flow with one element after it supports pagination

        let obj = LayoutObj::new(Frame::new(
            title,
            ButtonPage::new_str(
                Paragraphs::new([
                    Paragraph::new(&theme::TEXT_MONO, description.unwrap_or_default()),
                    Paragraph::new(&theme::TEXT_BOLD, data),
                ]),
                theme::BG,
            ),
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn confirm_properties(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;

        let mut paragraphs = ParagraphVecLong::new();

        let mut iter_buf = IterBuf::new();
        let iter = Iter::try_from_obj_with_buf(items, &mut iter_buf)?;
        for para in iter {
            let [key, value, _is_mono]: [Obj; 3] = iter_into_objs(para)?;
            let key = key.try_into_option::<StrBuffer>()?;
            let value = value.try_into_option::<StrBuffer>()?;

            if let Some(key) = key {
                if value.is_some() {
                    paragraphs.add(Paragraph::new(&theme::TEXT_BOLD, key).no_break());
                } else {
                    paragraphs.add(Paragraph::new(&theme::TEXT_BOLD, key));
                }
            }
            if let Some(value) = value {
                paragraphs.add(Paragraph::new(&theme::TEXT_MONO, value));
            }
        }

        let mut content = ButtonPage::new_str(paragraphs.into_paragraphs(), theme::BG);
        if hold {
            let confirm_btn =
                Some(ButtonDetails::text("CONFIRM").with_duration(Duration::from_secs(1)));
            content = content.with_confirm_btn(confirm_btn);
        }
        let obj = LayoutObj::new(Frame::new(title, content))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn confirm_output(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let address: StrBuffer = kwargs.get(Qstr::MP_QSTR_address)?.try_into()?;
        // Getting this from micropython so it is also a `StrBuffer`, not having
        // to handle the string operation in Rust, which would make it a `String`
        // (which would them cause issues with general `T: AsRef<str>` parameter)
        let truncated_address: StrBuffer =
            kwargs.get(Qstr::MP_QSTR_truncated_address)?.try_into()?;
        let amount: StrBuffer = kwargs.get(Qstr::MP_QSTR_amount)?.try_into()?;
        let title: StrBuffer = "SEND".into();

        let get_page = move |page_index| {
            // Showing two screens - the recipient address and summary confirmation
            match page_index {
                0 => {
                    // `icon + label + address`
                    let btn_layout = ButtonLayout::new(
                        Some(ButtonDetails::cancel_icon()),
                        None,
                        Some(ButtonDetails::text("CONTINUE")),
                    );
                    let btn_actions = ButtonActions::cancel_next();
                    Page::<20>::new(btn_layout, btn_actions, Font::MONO).icon_label_text(
                        theme::ICON_USER,
                        "Recipient".into(),
                        address.clone(),
                    )
                }
                1 => {
                    // 2 pairs `icon + label + text`
                    let btn_layout = ButtonLayout::new(
                        Some(ButtonDetails::cancel_icon()),
                        None,
                        Some(
                            ButtonDetails::text("HOLD TO CONFIRM")
                                .with_duration(Duration::from_secs(2)),
                        ),
                    );
                    let btn_actions = ButtonActions::cancel_confirm();
                    Page::<20>::new(btn_layout, btn_actions, Font::MONO)
                        .icon_label_text(
                            theme::ICON_USER,
                            "Recipient".into(),
                            truncated_address.clone(),
                        )
                        .newline()
                        .icon_label_text(theme::ICON_AMOUNT, "Amount".into(), amount.clone())
                }
                _ => unreachable!(),
            }
        };
        let pages = FlowPages::new(get_page, 2);

        let obj = LayoutObj::new(Flow::new(pages).with_common_title(title).into_child())?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn confirm_total(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let total_amount: StrBuffer = kwargs.get(Qstr::MP_QSTR_total_amount)?.try_into()?;
        let fee_amount: StrBuffer = kwargs.get(Qstr::MP_QSTR_fee_amount)?.try_into()?;
        let fee_rate_amount: Option<StrBuffer> = kwargs
            .get(Qstr::MP_QSTR_fee_rate_amount)?
            .try_into_option()?;
        let total_label: StrBuffer = kwargs.get(Qstr::MP_QSTR_total_label)?.try_into()?;
        let fee_label: StrBuffer = kwargs.get(Qstr::MP_QSTR_fee_label)?.try_into()?;

        let get_page = move |page_index| {
            // One page with 2 or 3 pairs `icon + label + text`
            assert!(page_index == 0);

            let btn_layout = ButtonLayout::new(
                Some(ButtonDetails::cancel_icon()),
                None,
                Some(ButtonDetails::text("HOLD TO SEND").with_duration(Duration::from_secs(2))),
            );
            let btn_actions = ButtonActions::cancel_confirm();

            let mut flow_page = Page::<25>::new(btn_layout, btn_actions, Font::MONO)
                .icon_label_text(theme::ICON_PARAM, total_label.clone(), total_amount.clone())
                .newline()
                .icon_label_text(theme::ICON_PARAM, fee_label.clone(), fee_amount.clone());

            if let Some(fee_rate_amount) = &fee_rate_amount {
                flow_page = flow_page.newline().icon_label_text(
                    theme::ICON_PARAM,
                    "Fee rate".into(),
                    fee_rate_amount.clone(),
                )
            }
            flow_page
        };
        let pages = FlowPages::new(get_page, 1);

        let obj = LayoutObj::new(Flow::new(pages).with_common_title(title).into_child())?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

/// General pattern of most tutorial screens.
/// (title, text, btn_layout, btn_actions)
fn tutorial_screen(
    data: (
        StrBuffer,
        StrBuffer,
        ButtonLayout<&'static str>,
        ButtonActions,
    ),
) -> Page<10> {
    let (title, text, btn_layout, btn_actions) = data;
    let mut page = Page::<10>::new(
        btn_layout,
        btn_actions,
        if !title.is_empty() {
            Font::BOLD
        } else {
            Font::MONO
        },
    );
    // Add title if present
    if !title.is_empty() {
        page = page.text_bold(title).newline().newline_half()
    }
    page = page.text_mono(text);
    page
}

extern "C" fn tutorial(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], _kwargs: &Map| {
        const PAGE_COUNT: u8 = 7;

        let get_page = |page_index| {
            // Lazy-loaded list of screens to show, with custom content,
            // buttons and actions triggered by these buttons.
            // Cancelling the first screen will point to the last one,
            // which asks for confirmation whether user wants to
            // really cancel the tutorial.
            match page_index {
                // title, text, btn_layout, btn_actions
                0 => {
                    tutorial_screen((
                        "HELLO".into(),
                        "Welcome to Trezor.\nPress right to continue.".into(),
                        ButtonLayout::cancel_and_arrow(),
                        ButtonActions::last_next(),
                    ))
                },
                1 => {
                    tutorial_screen((
                        "".into(),
                        "Use Trezor by clicking left and right.\n\nContinue right.".into(),
                        ButtonLayout::left_right_arrows(),
                        ButtonActions::prev_next(),
                    ))
                },
                2 => {
                    tutorial_screen((
                        "HOLD TO CONFIRM".into(),
                        "Press and hold right to approve important operations.".into(),
                        ButtonLayout::back_and_htc_text("HOLD TO CONFIRM", Duration::from_millis(1000)),
                        ButtonActions::prev_next(),
                    ))
                },
                3 => {
                    tutorial_screen((
                        "SCREEN SCROLL".into(),
                        "Press right to scroll down to read all content when text\ndoesn't fit on one screen. Press left to scroll up.".into(),
                        ButtonLayout::back_and_text("GOT IT"),
                        ButtonActions::prev_next(),
                    ))
                },
                4 => {
                    tutorial_screen((
                        "CONFIRM".into(),
                        "Press both left and right at the same time to confirm.".into(),
                        ButtonLayout::middle_armed_text("CONFIRM"),
                        ButtonActions::prev_next_with_middle(),
                    ))
                },
                // This page is special
                5 => {
                    Page::<10>::new(
                        ButtonLayout::left_right_text("AGAIN", "FINISH"),
                        ButtonActions::beginning_confirm(),
                        Font::MONO,
                    )
                        .newline()
                        .text_mono("Tutorial complete.".into())
                        .newline()
                        .newline()
                        .alignment(LineAlignment::Center)
                        .text_bold("You're ready to\nuse Trezor.".into())
                },
                6 => {
                    tutorial_screen((
                        "SKIP TUTORIAL".into(),
                        "Are you sure you want to skip the tutorial?".into(),
                        ButtonLayout::cancel_and_text("SKIP"),
                        ButtonActions::beginning_cancel(),
                    ))
                },
                _ => unreachable!(),
            }
        };

        let pages = FlowPages::new(get_page, PAGE_COUNT);

        let obj = LayoutObj::new(Flow::new(pages).into_child())?;
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
        let share_words: Vec<StrBuffer, 24> = iter_into_vec(share_words_obj)?;

        let confirm_btn =
            Some(ButtonDetails::text("CONFIRM").with_duration(Duration::from_secs(1)));

        let obj = LayoutObj::new(
            ButtonPage::new_str(ShareWords::new(share_words), theme::FG)
                .with_cancel_btn(None)
                .with_confirm_btn(confirm_btn)
                .with_scrollbar(false),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn select_word(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let words_iterable: Obj = kwargs.get(Qstr::MP_QSTR_words)?;
        let words: Vec<StrBuffer, 3> = iter_into_vec(words_iterable)?;

        // TODO: should return int, to be consistent with TT's select_word
        let obj = LayoutObj::new(Frame::new(
            title,
            SimpleChoice::new(words, true, true).into_child(),
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn request_word_count(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;

        let choices: Vec<&str, 3> = ["12", "18", "24"].into_iter().collect();

        let obj = LayoutObj::new(Frame::new(
            title,
            SimpleChoice::new(choices, false, false).into_child(),
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn request_word_bip39(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let prompt: StrBuffer = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;

        let obj = LayoutObj::new(Frame::new(prompt, Bip39Entry::new().into_child()))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn request_passphrase(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let prompt: StrBuffer = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let _max_len: u8 = kwargs.get(Qstr::MP_QSTR_max_len)?.try_into()?;

        let obj = LayoutObj::new(Frame::new(prompt, PassphraseEntry::new().into_child()))?;
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

    /// def confirm_properties(
    ///     *,
    ///     title: str,
    ///     items: Iterable[Tuple[str | None, str | None, bool]],
    ///     hold: bool = False,
    /// ) -> object:
    ///     """Confirm list of key-value pairs. The third component in the tuple should be True if
    ///     the value is to be rendered as binary with monospace font, False otherwise.
    ///     This only concerns the text style, you need to decode the value to UTF-8 in python."""
    Qstr::MP_QSTR_confirm_properties => obj_fn_kw!(0, confirm_properties).as_obj(),

    /// def confirm_output_r(
    ///     *,
    ///     address: str,
    ///     truncated_address: str,
    ///     amount: str,
    /// ) -> object:
    ///     """Confirm output. Specific for model R."""
    Qstr::MP_QSTR_confirm_output_r => obj_fn_kw!(0, confirm_output).as_obj(),

    /// def confirm_total_r(
    ///     *,
    ///     title: str,
    ///     total_amount: str,
    ///     fee_amount: str,
    ///     fee_rate_amount: str | None = None,
    ///     total_label: str,
    ///     fee_label: str,
    /// ) -> object:
    ///     """Confirm summary of a transaction. Specific for model R."""
    Qstr::MP_QSTR_confirm_total_r => obj_fn_kw!(0, confirm_total).as_obj(),

    /// def tutorial() -> object:
    ///     """Show user how to interact with the device."""
    Qstr::MP_QSTR_tutorial => obj_fn_kw!(0, tutorial).as_obj(),

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

    /// def select_word(
    ///     *,
    ///     title: str,
    ///     words: Iterable[str],
    /// ) -> str:
    ///    """Select a word from a list. TODO: should return int, to be consistent with TT's select_word"""
    Qstr::MP_QSTR_select_word => obj_fn_kw!(0, select_word).as_obj(),

    /// def request_word_count(
    ///     *,
    ///     title: str,
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
