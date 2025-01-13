use crate::{
    error::Error,
    io::BinaryData,
    micropython::{gc::Gc, list::List, obj::Obj},
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            text::{
                op::OpTextLayout,
                paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort},
            },
            Empty, FormattedText,
        },
        layout::{
            obj::{LayoutMaybeTrace, LayoutObj, RootComponent},
            util::{ConfirmValueParams, RecoveryType, StrOrBytes},
        },
        ui_firmware::{
            FirmwareUI, MAX_CHECKLIST_ITEMS, MAX_GROUP_SHARE_LINES, MAX_WORD_QUIZ_ITEMS,
        },
        ModelUI,
    },
};

use super::{
    component::{ActionBar, Button, Header, Hint, TextScreen},
    fonts, theme, UIEckhart,
};

impl FirmwareUI for UIEckhart {
    fn confirm_action(
        title: TString<'static>,
        action: Option<TString<'static>>,
        description: Option<TString<'static>>,
        _subtitle: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        _verb_cancel: Option<TString<'static>>,
        hold: bool,
        _hold_danger: bool,
        reverse: bool,
        _prompt_screen: bool,
        _prompt_title: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let action = action.unwrap_or("".into());
        let description = description.unwrap_or("".into());
        let formatted_text = {
            let ops = if !reverse {
                OpTextLayout::new(theme::TEXT_NORMAL)
                    .color(theme::GREY_LIGHT)
                    .text(action, fonts::FONT_SATOSHI_REGULAR_38)
                    .newline()
                    .color(theme::GREY)
                    .text(description, fonts::FONT_SATOSHI_REGULAR_22)
            } else {
                OpTextLayout::new(theme::TEXT_NORMAL)
                    .color(theme::GREY)
                    .text(description, fonts::FONT_SATOSHI_REGULAR_22)
                    .newline()
                    .color(theme::GREY_LIGHT)
                    .text(action, fonts::FONT_SATOSHI_REGULAR_38)
            };
            FormattedText::new(ops).vertically_centered()
        };

        let verb = verb.unwrap_or(TR::buttons__confirm.into());
        let right_button = if hold {
            Button::with_text(verb).with_long_press(theme::CONFIRM_HOLD_DURATION)
        } else {
            Button::with_text(verb)
        };
        let screen = TextScreen::new(formatted_text)
            .with_header(Header::new(title).with_menu_button())
            .with_hint(Hint::new_instruction(description, None))
            .with_action_bar(ActionBar::new_double(
                Button::with_icon(theme::ICON_CHEVRON_LEFT),
                right_button,
            ));
        let layout = RootComponent::new(screen);
        Ok(layout)
    }

    fn confirm_address(
        _title: TString<'static>,
        _address: Obj,
        _address_label: Option<TString<'static>>,
        _verb: Option<TString<'static>>,
        _info_button: bool,
        _chunkify: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        Err::<Gc<LayoutObj>, Error>(Error::ValueError(c"not implemented"))
    }

    fn confirm_homescreen(
        _title: TString<'static>,
        _image: BinaryData<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn confirm_coinjoin(
        _max_rounds: TString<'static>,
        _max_feerate: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn confirm_emphasized(
        _title: TString<'static>,
        _items: Obj,
        _verb: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn confirm_fido(
        _title: TString<'static>,
        _app_name: TString<'static>,
        _icon: Option<TString<'static>>,
        _accounts: Gc<List>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        #[cfg(feature = "universal_fw")]
        return Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"));
        #[cfg(not(feature = "universal_fw"))]
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(
            c"confirm_fido not used in bitcoin-only firmware",
        ))
    }

    fn confirm_firmware_update(
        _description: TString<'static>,
        _fingerprint: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn confirm_modify_fee(
        _title: TString<'static>,
        _sign: i32,
        _user_fee_change: TString<'static>,
        _total_fee_new: TString<'static>,
        _fee_rate_amount: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn confirm_modify_output(
        _sign: i32,
        _amount_change: TString<'static>,
        _amount_new: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn confirm_more(
        _title: TString<'static>,
        _button: TString<'static>,
        _button_style_confirm: bool,
        _items: Obj,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn confirm_reset_device(_recovery: bool) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn confirm_summary(
        _amount: TString<'static>,
        _amount_label: TString<'static>,
        _fee: TString<'static>,
        _fee_label: TString<'static>,
        _title: Option<TString<'static>>,
        _account_items: Option<Obj>,
        _extra_items: Option<Obj>,
        _extra_title: Option<TString<'static>>,
        _verb_cancel: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn confirm_properties(
        _title: TString<'static>,
        _items: Obj,
        _hold: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn confirm_value(
        _title: TString<'static>,
        _value: Obj,
        _description: Option<TString<'static>>,
        _is_data: bool,
        _extra: Option<TString<'static>>,
        _subtitle: Option<TString<'static>>,
        _verb: Option<TString<'static>>,
        _verb_cancel: Option<TString<'static>>,
        _info: bool,
        _hold: bool,
        _chunkify: bool,
        _page_counter: bool,
        _prompt_screen: bool,
        _cancel: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        Err::<Gc<LayoutObj>, Error>(Error::ValueError(c"not implemented"))
    }

    fn confirm_value_intro(
        _title: TString<'static>,
        _value: Obj,
        _subtitle: Option<TString<'static>>,
        _verb: Option<TString<'static>>,
        _verb_cancel: Option<TString<'static>>,
        _chunkify: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        Err::<Gc<LayoutObj>, Error>(Error::ValueError(c"confirm_value_intro not implemented"))
    }

    fn confirm_with_info(
        _title: TString<'static>,
        _button: TString<'static>,
        _info_button: TString<'static>,
        _verb_cancel: Option<TString<'static>>,
        _items: Obj,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn check_homescreen_format(_image: BinaryData, _accept_toif: bool) -> bool {
        false // not implemented
    }

    fn continue_recovery_homepage(
        _text: TString<'static>,
        _subtext: Option<TString<'static>>,
        _button: Option<TString<'static>>,
        _recovery_type: RecoveryType,
        _show_instructions: bool,
        _remaining_shares: Option<Obj>,
    ) -> Result<Gc<LayoutObj>, Error> {
        Err::<Gc<LayoutObj>, Error>(Error::ValueError(c"not implemented"))
    }

    fn flow_confirm_output(
        _title: Option<TString<'static>>,
        _subtitle: Option<TString<'static>>,
        _description: Option<TString<'static>>,
        _extra: Option<TString<'static>>,
        _message: Obj,
        _amount: Option<Obj>,
        _chunkify: bool,
        _text_mono: bool,
        _account_title: TString<'static>,
        _account: Option<TString<'static>>,
        _account_path: Option<TString<'static>>,
        _br_code: u16,
        _br_name: TString<'static>,
        _address: Option<Obj>,
        _address_title: Option<TString<'static>>,
        _summary_items: Option<Obj>,
        _fee_items: Option<Obj>,
        _summary_title: Option<TString<'static>>,
        _summary_br_code: Option<u16>,
        _summary_br_name: Option<TString<'static>>,
        _cancel_text: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn flow_confirm_set_new_pin(
        _title: TString<'static>,
        _description: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn flow_get_address(
        _address: Obj,
        _title: TString<'static>,
        _description: Option<TString<'static>>,
        _extra: Option<TString<'static>>,
        _chunkify: bool,
        _address_qr: TString<'static>,
        _case_sensitive: bool,
        _account: Option<TString<'static>>,
        _path: Option<TString<'static>>,
        _xpubs: Obj,
        _title_success: TString<'static>,
        _br_code: u16,
        _br_name: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn multiple_pages_texts(
        _title: TString<'static>,
        _verb: TString<'static>,
        _items: Gc<List>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn prompt_backup() -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn request_bip39(
        _prompt: TString<'static>,
        _prefill_word: TString<'static>,
        _can_go_back: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn request_slip39(
        _prompt: TString<'static>,
        _prefill_word: TString<'static>,
        _can_go_back: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn request_number(
        _title: TString<'static>,
        _count: u32,
        _min_count: u32,
        _max_count: u32,
        _description: Option<TString<'static>>,
        _more_info_callback: Option<impl Fn(u32) -> TString<'static> + 'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn request_pin(
        _prompt: TString<'static>,
        _subprompt: TString<'static>,
        _allow_cancel: bool,
        _warning: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn request_passphrase(
        _prompt: TString<'static>,
        _max_len: u32,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn select_word(
        _title: TString<'static>,
        _description: TString<'static>,
        _words: [TString<'static>; MAX_WORD_QUIZ_ITEMS],
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn select_word_count(_recovery_type: RecoveryType) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn set_brightness(_current_brightness: Option<u8>) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn show_address_details(
        _qr_title: TString<'static>,
        _address: TString<'static>,
        _case_sensitive: bool,
        _details_title: TString<'static>,
        _account: Option<TString<'static>>,
        _path: Option<TString<'static>>,
        _xpubs: Obj,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn show_checklist(
        _title: TString<'static>,
        _button: TString<'static>,
        _active: usize,
        _items: [TString<'static>; MAX_CHECKLIST_ITEMS],
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn show_danger(
        _title: TString<'static>,
        _description: TString<'static>,
        _value: TString<'static>,
        _verb_cancel: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn show_error(
        _title: TString<'static>,
        _button: TString<'static>,
        _description: TString<'static>,
        _allow_cancel: bool,
        _time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error> {
        Err::<Gc<LayoutObj>, Error>(Error::ValueError(c"not implemented"))
    }

    fn show_group_share_success(
        _lines: [TString<'static>; MAX_GROUP_SHARE_LINES],
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn show_homescreen(
        label: TString<'static>,
        _hold: bool,
        notification: Option<TString<'static>>,
        _notification_level: u8,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let paragraphs = ParagraphVecShort::from_iter([
            Paragraph::new(&theme::TEXT_NORMAL, label),
            Paragraph::new(
                &theme::TEXT_NORMAL,
                notification.unwrap_or(TString::empty()),
            ),
        ])
        .into_paragraphs();

        let layout = RootComponent::new(paragraphs);
        Ok(layout)
    }

    fn show_info(
        _title: TString<'static>,
        _description: TString<'static>,
        _button: TString<'static>,
        _time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error> {
        Err::<Gc<LayoutObj>, Error>(Error::ValueError(c"not implemented"))
    }

    fn show_info_with_cancel(
        _title: TString<'static>,
        _items: Obj,
        _horizontal: bool,
        _chunkify: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn show_lockscreen(
        _label: TString<'static>,
        _bootscreen: bool,
        _coinjoin_authorized: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn show_mismatch(_title: TString<'static>) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn show_progress(
        _description: TString<'static>,
        _indeterminate: bool,
        _title: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn show_progress_coinjoin(
        _title: TString<'static>,
        _indeterminate: bool,
        _time_ms: u32,
        _skip_first_paint: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        Err::<Gc<LayoutObj>, Error>(Error::ValueError(c"not implemented"))
    }

    fn show_share_words(
        _words: heapless::Vec<TString<'static>, 33>,
        _title: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn show_share_words_delizia(
        _words: heapless::Vec<TString<'static>, 33>,
        _subtitle: Option<TString<'static>>,
        _instructions: Obj,
        _text_footer: Option<TString<'static>>,
        _text_confirm: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn show_remaining_shares(_pages_iterable: Obj) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn show_simple(
        text: TString<'static>,
        _title: Option<TString<'static>>,
        _button: Option<TString<'static>>,
    ) -> Result<Gc<LayoutObj>, Error> {
        Err::<Gc<LayoutObj>, Error>(Error::ValueError(c"not implemented"))
    }

    fn show_success(
        _title: TString<'static>,
        _button: TString<'static>,
        _description: TString<'static>,
        _allow_cancel: bool,
        _time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error> {
        Err::<Gc<LayoutObj>, Error>(Error::ValueError(c"not implemented"))
    }

    fn show_wait_text(_text: TString<'static>) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn show_warning(
        _title: TString<'static>,
        _button: TString<'static>,
        _value: TString<'static>,
        _description: TString<'static>,
        _allow_cancel: bool,
        _danger: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        Err::<Gc<LayoutObj>, Error>(Error::ValueError(c"not implemented"))
    }

    fn tutorial() -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }
}
