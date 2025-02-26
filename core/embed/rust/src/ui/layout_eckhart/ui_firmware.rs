use crate::{
    error::Error,
    io::BinaryData,
    micropython::{gc::Gc, iter::IterBuf, list::List, obj::Obj, util},
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            text::{
                op::OpTextLayout,
                paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort, VecExt},
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
    component::{
        ActionBar, Bip39Input, Button, Header, HeaderMsg, Hint, MnemonicKeyboard, PinKeyboard,
        SelectWordCountScreen, SelectWordScreen, Slip39Input, TextScreen,
    },
    flow, fonts, theme, UIEckhart,
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
        _hold: bool,
        _items: Obj,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn confirm_reset_device(recovery: bool) -> Result<impl LayoutMaybeTrace, Error> {
        let flow = flow::confirm_reset::new_confirm_reset(recovery)?;
        Ok(flow)
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
        title: TString<'static>,
        value: Obj,
        description: Option<TString<'static>>,
        is_data: bool,
        extra: Option<TString<'static>>,
        _subtitle: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        _verb_cancel: Option<TString<'static>>,
        info: bool,
        hold: bool,
        chunkify: bool,
        page_counter: bool,
        _prompt_screen: bool,
        _cancel: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        let paragraphs = ConfirmValueParams {
            description: description.unwrap_or("".into()),
            extra: extra.unwrap_or("".into()),
            value: if value != Obj::const_none() {
                value.try_into()?
            } else {
                StrOrBytes::Str("".into())
            },
            font: if chunkify {
                let value: TString = value.try_into()?;
                theme::get_chunkified_text_style(value.len())
            } else if is_data {
                &theme::TEXT_MONO_MEDIUM
            } else {
                &theme::TEXT_MEDIUM
            },
            description_font: &theme::TEXT_SMALL,
            extra_font: &theme::TEXT_SMALL,
        }
        .into_paragraphs();

        let verb = verb.unwrap_or(TR::buttons__confirm.into());
        let right_button = if hold {
            Button::with_text(verb).with_long_press(theme::CONFIRM_HOLD_DURATION)
        } else {
            Button::with_text(verb)
        };
        let header = if info {
            Header::new(title)
                .with_right_button(Button::with_icon(theme::ICON_INFO), HeaderMsg::Menu)
        } else {
            Header::new(title)
        };

        let mut screen = TextScreen::new(paragraphs)
            .with_header(header)
            .with_action_bar(ActionBar::new_double(
                Button::with_icon(theme::ICON_CROSS),
                right_button,
            ));
        if page_counter {
            screen = screen.with_hint(Hint::new_page_counter());
        }
        LayoutObj::new(screen)
    }

    fn confirm_value_intro(
        _title: TString<'static>,
        _value: Obj,
        _subtitle: Option<TString<'static>>,
        _verb: Option<TString<'static>>,
        _verb_cancel: Option<TString<'static>>,
        _hold: bool,
        _chunkify: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        Err::<Gc<LayoutObj>, Error>(Error::ValueError(c"confirm_value_intro not implemented"))
    }

    fn confirm_with_info(
        _title: TString<'static>,
        _items: Obj,
        _verb: TString<'static>,
        _verb_info: TString<'static>,
        _verb_cancel: Option<TString<'static>>,
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
        _address_item: Option<(TString<'static>, Obj)>,
        _extra_item: Option<(TString<'static>, Obj)>,
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
        let flow = flow::prompt_backup::new_prompt_backup()?;
        Ok(flow)
    }

    fn request_bip39(
        prompt: TString<'static>,
        prefill_word: TString<'static>,
        can_go_back: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let layout = RootComponent::new(MnemonicKeyboard::new(
            prefill_word.map(Bip39Input::prefilled_word),
            prompt,
            can_go_back,
        ));
        Ok(layout)
    }

    fn request_slip39(
        prompt: TString<'static>,
        prefill_word: TString<'static>,
        can_go_back: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let layout = RootComponent::new(MnemonicKeyboard::new(
            prefill_word.map(Slip39Input::prefilled_word),
            prompt,
            can_go_back,
        ));

        Ok(layout)
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
        prompt: TString<'static>,
        subprompt: TString<'static>,
        allow_cancel: bool,
        warning: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let warning = if warning {
            Some(TR::pin__wrong_pin.into())
        } else {
            None
        };

        let layout = RootComponent::new(PinKeyboard::new(prompt, subprompt, warning, allow_cancel));
        Ok(layout)
    }

    fn request_passphrase(
        _prompt: TString<'static>,
        _max_len: u32,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let flow = flow::request_passphrase::new_request_passphrase()?;
        Ok(flow)
    }

    fn select_word(
        title: TString<'static>,
        description: TString<'static>,
        words: [TString<'static>; MAX_WORD_QUIZ_ITEMS],
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let component = SelectWordScreen::new(words, description).with_header(
            Header::new(title)
                .with_right_button(Button::with_icon(theme::ICON_MENU), HeaderMsg::Cancelled),
        );

        let layout = RootComponent::new(component);

        Ok(layout)
    }

    fn select_word_count(recovery_type: RecoveryType) -> Result<impl LayoutMaybeTrace, Error> {
        let description = TR::recovery__num_of_words.into();
        let content = if matches!(recovery_type, RecoveryType::UnlockRepeatedBackup) {
            SelectWordCountScreen::new_multi_share(description)
        } else {
            SelectWordCountScreen::new_single_share(description)
        }
        .with_header(Header::new(TR::recovery__title_recover.into()));
        let layout = RootComponent::new(content);
        Ok(layout)
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
        title: TString<'static>,
        items: Obj,
        _horizontal: bool,
        chunkify: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let mut paragraphs = ParagraphVecShort::new();
        for para in IterBuf::new().try_iterate(items)? {
            let [key, value]: [Obj; 2] = util::iter_into_array(para)?;
            let key: TString = key.try_into()?;
            let value: TString = value.try_into()?;
            paragraphs.add(Paragraph::new(&theme::TEXT_MEDIUM, key).no_break());
            if chunkify {
                paragraphs.add(Paragraph::new(
                    theme::get_chunkified_text_style(value.len()),
                    value,
                ));
            } else {
                paragraphs.add(Paragraph::new(&theme::TEXT_MONO_MEDIUM, value));
            }
        }

        let screen = TextScreen::new(paragraphs.into_paragraphs())
            .with_header(Header::new(title).with_close_button());
        let layout = RootComponent::new(screen);
        Ok(layout)
    }

    fn show_lockscreen(
        _label: TString<'static>,
        _bootscreen: bool,
        _coinjoin_authorized: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn show_mismatch(title: TString<'static>) -> Result<impl LayoutMaybeTrace, Error> {
        let description: TString = TR::addr_mismatch__contact_support_at.into();
        let url: TString = TR::addr_mismatch__support_url.into();
        let button: TString = TR::buttons__quit.into();

        let paragraphs = ParagraphVecShort::from_iter([
            Paragraph::new(&theme::TEXT_REGULAR, description).centered(),
            Paragraph::new(&theme::TEXT_MONO_MEDIUM, url).centered(),
        ])
        .into_paragraphs();
        let screen = TextScreen::new(paragraphs)
            .with_header(Header::new(title))
            .with_action_bar(ActionBar::new_single(Button::with_text(button)));

        let layout = RootComponent::new(screen);
        Ok(layout)
    }

    fn show_progress(
        description: TString<'static>,
        _indeterminate: bool,
        title: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let (title, description) = if let Some(title) = title {
            (title, description)
        } else {
            (description, "".into())
        };

        let paragraphs = Paragraph::new(&theme::TEXT_REGULAR, description)
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical());
        let header = Header::new(title);
        let screen = TextScreen::new(paragraphs).with_header(header);

        let layout = RootComponent::new(screen);
        Ok(layout)
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
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(
            c"use show_share_words_extended instead",
        ))
    }

    fn show_share_words_extended(
        words: heapless::Vec<TString<'static>, 33>,
        subtitle: Option<TString<'static>>,
        instructions: Obj,
        // Irrelevant for Eckhart because the footer is dynamic
        _text_footer: Option<TString<'static>>,
        text_confirm: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        // TODO: add support for multiple instructions
        let instruction: TString = IterBuf::new()
            .try_iterate(instructions)?
            .next()
            .unwrap()
            .try_into()?;

        let flow = flow::show_share_words::new_show_share_words_flow(
            words,
            subtitle.unwrap_or(TString::empty()),
            Paragraph::new(&theme::TEXT_REGULAR, instruction),
            text_confirm,
        )?;
        Ok(flow)
    }

    fn show_remaining_shares(_pages_iterable: Obj) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }

    fn show_simple(
        text: TString<'static>,
        title: Option<TString<'static>>,
        button: Option<TString<'static>>,
    ) -> Result<Gc<LayoutObj>, Error> {
        let paragraphs = Paragraph::new(&theme::TEXT_REGULAR, text).into_paragraphs();

        let mut screen = TextScreen::new(paragraphs);
        if let Some(title) = title {
            screen = screen.with_header(Header::new(title));
        }
        if let Some(button) = button {
            screen = screen.with_action_bar(ActionBar::new_single(Button::with_text(button)));
        }

        let obj = LayoutObj::new(screen)?;
        Ok(obj)
    }

    fn show_success(
        title: TString<'static>,
        button: TString<'static>,
        description: TString<'static>,
        allow_cancel: bool,
        _time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error> {
        let paragraphs = Paragraph::new(&theme::TEXT_REGULAR, description).into_paragraphs();
        let header = Header::new(title).with_icon(theme::ICON_DONE, theme::GREEN_LIGHT);
        let action_bar = if allow_cancel {
            ActionBar::new_double(
                Button::with_icon(theme::ICON_CROSS),
                Button::with_text(button),
            )
        } else {
            ActionBar::new_single(Button::with_text(button))
        };
        let screen = TextScreen::new(paragraphs)
            .with_header(header)
            .with_action_bar(action_bar);
        let layout = LayoutObj::new(screen)?;
        Ok(layout)
    }

    fn show_wait_text(text: TString<'static>) -> Result<impl LayoutMaybeTrace, Error> {
        let paragraphs = Paragraph::new(&theme::TEXT_REGULAR, text).into_paragraphs();
        let screen = TextScreen::new(paragraphs);
        let layout = RootComponent::new(screen);
        Ok(layout)
    }

    fn show_warning(
        title: TString<'static>,
        button: TString<'static>,
        value: TString<'static>,
        description: TString<'static>,
        allow_cancel: bool,
        _danger: bool, // TODO: review if `danger` needed in all layouts since we have show_danger
    ) -> Result<Gc<LayoutObj>, Error> {
        let paragraphs = ParagraphVecShort::from_iter([
            Paragraph::new(&theme::TEXT_SMALL, description),
            Paragraph::new(&theme::TEXT_REGULAR, value),
        ])
        .into_paragraphs();

        let header = Header::new(title).with_icon(theme::ICON_INFO, theme::GREEN_LIGHT);
        let action_bar = if allow_cancel {
            ActionBar::new_double(
                Button::with_icon(theme::ICON_CROSS),
                Button::with_text(button),
            )
        } else {
            ActionBar::new_single(Button::with_text(button))
        };
        let screen = TextScreen::new(paragraphs)
            .with_header(header)
            .with_action_bar(action_bar);
        let layout = LayoutObj::new(screen)?;
        Ok(layout)
    }

    fn tutorial() -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"not implemented"))
    }
}
