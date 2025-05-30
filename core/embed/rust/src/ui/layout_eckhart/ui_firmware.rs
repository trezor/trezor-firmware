use core::cmp::Ordering;

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
                paragraphs::{
                    Checklist, Paragraph, ParagraphSource, ParagraphVecLong, ParagraphVecShort,
                    Paragraphs, VecExt,
                },
                TextStyle,
            },
            ComponentExt as _, Empty, FormattedText, Timeout,
        },
        geometry::{Alignment, LinearPlacement, Offset},
        layout::{
            obj::{LayoutMaybeTrace, LayoutObj, RootComponent},
            util::{ConfirmValueParams, PropsList, RecoveryType, StrOrBytes},
        },
        ui_firmware::{
            FirmwareUI, MAX_CHECKLIST_ITEMS, MAX_GROUP_SHARE_LINES, MAX_WORD_QUIZ_ITEMS,
        },
        ModelUI,
    },
};

use super::{
    component::Button,
    firmware::{
        ActionBar, Bip39Input, ConfirmHomescreen, DeviceMenuScreen, Header, HeaderMsg, Hint,
        Homescreen, MnemonicKeyboard, PinKeyboard, ProgressScreen, SelectWordCountScreen,
        SelectWordScreen, SetBrightnessScreen, Slip39Input, TextScreen,
    },
    flow, fonts, theme, UIEckhart,
};

use heapless::Vec;

impl FirmwareUI for UIEckhart {
    fn confirm_action(
        title: TString<'static>,
        action: Option<TString<'static>>,
        description: Option<TString<'static>>,
        subtitle: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        _verb_cancel: Option<TString<'static>>,
        hold: bool,
        _hold_danger: bool,
        reverse: bool,
        _prompt_screen: bool,
        _prompt_title: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let paragraphs = {
            let action = action.unwrap_or("".into());
            let description = description.unwrap_or("".into());
            let mut paragraphs = ParagraphVecShort::new();
            if !reverse {
                paragraphs
                    .add(Paragraph::new(&theme::TEXT_REGULAR, action))
                    .add(Paragraph::new(&theme::TEXT_REGULAR, description));
            } else {
                paragraphs
                    .add(Paragraph::new(&theme::TEXT_REGULAR, description))
                    .add(Paragraph::new(&theme::TEXT_REGULAR, action));
            }
            paragraphs.into_paragraphs().with_placement(
                LinearPlacement::vertical().with_spacing(theme::TEXT_VERTICAL_SPACING),
            )
        };

        let verb = verb.unwrap_or(TR::buttons__confirm.into());
        let mut right_button = Button::with_text(verb).styled(theme::firmware::button_confirm());
        if hold {
            right_button = right_button.with_long_press(theme::CONFIRM_HOLD_DURATION);
        }

        let mut screen = TextScreen::new(paragraphs)
            .with_header(Header::new(title))
            .with_action_bar(ActionBar::new_double(
                Button::with_icon(theme::ICON_CROSS),
                right_button,
            ));
        if let Some(subtitle) = subtitle {
            screen = screen.with_hint(Hint::new_instruction(subtitle, None));
        }
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
        title: TString<'static>,
        image: BinaryData<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let screen = ConfirmHomescreen::new(title, image)?;
        let layout = RootComponent::new(screen);
        Ok(layout)
    }

    fn confirm_coinjoin(
        max_rounds: TString<'static>,
        max_feerate: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let paragraphs = ParagraphVecShort::from_iter([
            Paragraph::new(&theme::TEXT_REGULAR, TR::coinjoin__max_rounds),
            Paragraph::new(&theme::TEXT_MONO_LIGHT, max_rounds),
            Paragraph::new(&theme::TEXT_REGULAR, TR::coinjoin__max_mining_fee),
            Paragraph::new(&theme::TEXT_MONO_LIGHT, max_feerate),
        ])
        .into_paragraphs()
        .with_placement(LinearPlacement::vertical());

        let screen = TextScreen::new(paragraphs)
            .with_header(Header::new(TR::coinjoin__title.into()))
            .with_action_bar(ActionBar::new_cancel_confirm());
        let layout = RootComponent::new(screen);
        Ok(layout)
    }

    fn confirm_emphasized(
        title: TString<'static>,
        items: Obj,
        verb: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let font = fonts::FONT_SATOSHI_REGULAR_38;
        let text_style = theme::firmware::TEXT_REGULAR;
        let mut ops = OpTextLayout::new(text_style);

        for item in IterBuf::new().try_iterate(items)? {
            if item.is_str() {
                ops = ops.text(TString::try_from(item)?, font)
            } else {
                let [emphasis, text]: [Obj; 2] = util::iter_into_array(item)?;
                let text: TString = text.try_into()?;
                if emphasis.try_into()? {
                    ops = ops.color(theme::WHITE);
                    ops = ops.text(text, font);
                    ops = ops.color(text_style.text_color);
                } else {
                    ops = ops.text(text, font);
                }
            }
        }
        let text = FormattedText::new(ops);
        let action_bar = ActionBar::new_double(
            Button::with_icon(theme::ICON_CROSS),
            Button::with_text(verb.unwrap_or(TR::buttons__confirm.into())),
        );
        let screen = TextScreen::new(text)
            .with_header(Header::new(title))
            .with_action_bar(action_bar);
        let layout = RootComponent::new(screen);
        Ok(layout)
    }

    fn confirm_fido(
        title: TString<'static>,
        app_name: TString<'static>,
        icon: Option<TString<'static>>,
        accounts: Gc<List>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        #[cfg(feature = "universal_fw")]
        return flow::confirm_fido::new_confirm_fido(title, app_name, icon, accounts);
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
        title: TString<'static>,
        sign: i32,
        user_fee_change: TString<'static>,
        total_fee_new: TString<'static>,
        _fee_rate_amount: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let (description, change, total_label) = match sign {
            s if s < 0 => (
                TR::modify_fee__decrease_fee,
                user_fee_change,
                TR::modify_fee__new_transaction_fee,
            ),
            s if s > 0 => (
                TR::modify_fee__increase_fee,
                user_fee_change,
                TR::modify_fee__new_transaction_fee,
            ),
            _ => (
                TR::modify_fee__no_change,
                "".into(),
                TR::modify_fee__transaction_fee,
            ),
        };

        let paragraphs = ParagraphVecShort::from_iter([
            Paragraph::new(&theme::TEXT_SMALL_LIGHT, description),
            Paragraph::new(&theme::TEXT_MONO_MEDIUM_LIGHT, change),
            Paragraph::new(&theme::TEXT_SMALL_LIGHT, total_label),
            Paragraph::new(&theme::TEXT_MONO_MEDIUM_LIGHT, total_fee_new),
        ]);

        let flow = flow::new_confirm_with_menu(
            title,
            None,
            paragraphs
                .into_paragraphs()
                .with_spacing(12)
                .with_placement(LinearPlacement::vertical()),
            None,
            false,
            Some(TR::words__title_information.into()),
            None,
        )?;
        Ok(flow)
    }

    fn confirm_modify_output(
        sign: i32,
        amount_change: TString<'static>,
        amount_new: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let description = if sign < 0 {
            TR::modify_amount__decrease_amount
        } else {
            TR::modify_amount__increase_amount
        };

        let paragraphs = ParagraphVecShort::from_iter([
            Paragraph::new(&theme::TEXT_SMALL_LIGHT, description),
            Paragraph::new(&theme::TEXT_MONO_MEDIUM_LIGHT, amount_change),
            Paragraph::new(&theme::TEXT_SMALL_LIGHT, TR::modify_amount__new_amount),
            Paragraph::new(&theme::TEXT_MONO_MEDIUM_LIGHT, amount_new),
        ]);

        let layout = RootComponent::new(
            TextScreen::new(
                paragraphs
                    .into_paragraphs()
                    .with_placement(LinearPlacement::vertical())
                    .with_spacing(12),
            )
            .with_header(Header::new(TR::modify_amount__title.into()))
            .with_action_bar(ActionBar::new_double(
                Button::with_icon(theme::ICON_CROSS),
                Button::with_text(TR::buttons__confirm.into()),
            )),
        );
        Ok(layout)
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
        amount: Option<TString<'static>>,
        amount_label: Option<TString<'static>>,
        fee: TString<'static>,
        fee_label: TString<'static>,
        title: Option<TString<'static>>,
        account_items: Option<Obj>,
        account_title: Option<TString<'static>>,
        extra_items: Option<Obj>,
        extra_title: Option<TString<'static>>,
        verb_cancel: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        // collect available info
        let account_paragraphs = if let Some(items) = account_items {
            let mut paragraphs = ParagraphVecShort::new();
            for pair in IterBuf::new().try_iterate(items)? {
                let [label, value]: [TString; 2] = util::iter_into_array(pair)?;
                unwrap!(paragraphs.push(Paragraph::new(&theme::TEXT_SMALL_LIGHT, label).no_break()));
                unwrap!(paragraphs.push(Paragraph::new(&theme::TEXT_MONO_LIGHT, value)));
            }
            Some(paragraphs)
        } else {
            None
        };
        let extra_paragraphs = if let Some(items) = extra_items {
            let mut paragraphs = ParagraphVecShort::new();
            for pair in IterBuf::new().try_iterate(items)? {
                let [label, value]: [TString; 2] = util::iter_into_array(pair)?;
                unwrap!(paragraphs.push(Paragraph::new(&theme::TEXT_SMALL_LIGHT, label).no_break()));
                unwrap!(paragraphs.push(Paragraph::new(&theme::TEXT_MONO_LIGHT, value)));
            }
            Some(paragraphs)
        } else {
            None
        };

        let flow = flow::new_confirm_summary(
            title.unwrap_or(TString::empty()),
            amount,
            amount_label,
            fee,
            fee_label,
            account_title,
            account_paragraphs,
            extra_title,
            extra_paragraphs,
            verb_cancel,
        )?;
        Ok(flow)
    }

    fn confirm_properties(
        title: TString<'static>,
        items: Obj,
        hold: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let paragraphs = PropsList::new(
            items,
            &theme::TEXT_SMALL_LIGHT,
            &theme::TEXT_MEDIUM,
            &theme::TEXT_MONO_LIGHT,
        )?;

        let flow = flow::new_confirm_with_menu(
            title,
            None,
            paragraphs
                .into_paragraphs()
                .with_spacing(12)
                .with_placement(LinearPlacement::vertical()),
            None,
            hold,
            None,
            None,
        )?;
        Ok(flow)
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
        title: TString<'static>,
        value: Obj,
        subtitle: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        verb_cancel: Option<TString<'static>>,
        hold: bool,
        chunkify: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        let flow = flow::new_confirm_value_intro(
            title,
            subtitle,
            value,
            TR::buttons__view_all_data.into(),
            verb_cancel,
            verb,
            hold,
            chunkify,
        )?;

        LayoutObj::new_root(flow)
    }

    fn confirm_with_info(
        title: TString<'static>,
        items: Obj,
        verb: TString<'static>,
        verb_info: TString<'static>,
        _verb_cancel: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let mut paragraphs = ParagraphVecShort::new();

        for para in IterBuf::new().try_iterate(items)? {
            let [text, is_data]: [Obj; 2] = util::iter_into_array(para)?;
            let is_data = is_data.try_into()?;
            let style: &TextStyle = if is_data {
                &theme::TEXT_MONO_MEDIUM_LIGHT
            } else {
                &theme::TEXT_SMALL_LIGHT
            };
            let text: TString = text.try_into()?;
            paragraphs.add(Paragraph::new(style, text));
            if paragraphs.is_full() {
                break;
            }
        }

        let flow = flow::new_confirm_with_menu(
            title,
            None,
            paragraphs
                .into_paragraphs()
                .with_placement(LinearPlacement::vertical())
                .with_spacing(12),
            Some(verb),
            false,
            Some(verb_info),
            None,
        )?;
        Ok(flow)
    }

    fn check_homescreen_format(image: BinaryData, _accept_toif: bool) -> bool {
        super::firmware::check_homescreen_format(image)
    }

    fn continue_recovery_homepage(
        text: TString<'static>,
        subtext: Option<TString<'static>>,
        _button: Option<TString<'static>>,
        recovery_type: RecoveryType,
        show_instructions: bool,
        remaining_shares: Option<Obj>,
    ) -> Result<Gc<LayoutObj>, Error> {
        let pages_vec = if let Some(pages_obj) = remaining_shares {
            let mut vec = ParagraphVecLong::new();
            for page in IterBuf::new().try_iterate(pages_obj)? {
                let [title, description]: [TString; 2] = util::iter_into_array(page)?;
                vec.add(Paragraph::new(&theme::TEXT_REGULAR, title))
                    .add(Paragraph::new(&theme::TEXT_MONO_LIGHT, description).break_after());
            }
            Some(vec)
        } else {
            None
        };

        let flow = flow::continue_recovery_homepage::new_continue_recovery_homepage(
            text,
            subtext,
            recovery_type,
            show_instructions,
            pages_vec,
        )?;
        LayoutObj::new_root(flow)
    }

    fn flow_confirm_output(
        title: Option<TString<'static>>,
        subtitle: Option<TString<'static>>,
        _description: Option<TString<'static>>,
        _extra: Option<TString<'static>>,
        message: Obj,
        amount: Option<Obj>,
        chunkify: bool,
        _text_mono: bool,
        account_title: TString<'static>,
        account: Option<TString<'static>>,
        account_path: Option<TString<'static>>,
        br_code: u16,
        br_name: TString<'static>,
        address_item: Option<(TString<'static>, Obj)>,
        _extra_item: Option<(TString<'static>, Obj)>,
        summary_items: Option<Obj>,
        fee_items: Option<Obj>,
        summary_title: Option<TString<'static>>,
        summary_br_code: Option<u16>,
        summary_br_name: Option<TString<'static>>,
        cancel_text: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let (address_title, address_paragraphs) = if let Some(address_item) = address_item {
            let mut paragraphs = ParagraphVecShort::new();
            for pair in IterBuf::new().try_iterate(address_item.1)? {
                let [label, value]: [TString; 2] = util::iter_into_array(pair)?;
                unwrap!(paragraphs.push(Paragraph::new(&theme::TEXT_SMALL_LIGHT, label).no_break()));
                unwrap!(paragraphs.push(Paragraph::new(&theme::TEXT_MONO_MEDIUM_LIGHT, value)));
            }
            (Some(address_item.0), Some(paragraphs))
        } else {
            (None, None)
        };

        // collect available info
        let account_paragraphs = {
            let mut paragraphs = ParagraphVecShort::new();
            if let Some(account) = account {
                unwrap!(paragraphs.push(
                    Paragraph::new(
                        &theme::TEXT_SMALL_LIGHT,
                        TString::from_translation(TR::words__wallet)
                    )
                    .no_break()
                ));
                unwrap!(paragraphs.push(Paragraph::new(&theme::TEXT_MONO_LIGHT, account)));
            }
            if let Some(path) = account_path {
                unwrap!(paragraphs.push(
                    Paragraph::new(
                        &theme::TEXT_SMALL_LIGHT,
                        TString::from_translation(TR::address_details__derivation_path)
                    )
                    .no_break()
                ));
                unwrap!(paragraphs.push(Paragraph::new(&theme::TEXT_MONO_LIGHT, path)));
            }
            if paragraphs.is_empty() {
                None
            } else {
                Some(paragraphs)
            }
        };

        let summary_paragraphs = if let Some(items) = summary_items {
            let mut paragraphs = ParagraphVecShort::new();
            for pair in IterBuf::new().try_iterate(items)? {
                let [label, value]: [TString; 2] = util::iter_into_array(pair)?;
                unwrap!(paragraphs.push(Paragraph::new(&theme::TEXT_SMALL_LIGHT, label).no_break()));
                unwrap!(paragraphs.push(Paragraph::new(&theme::TEXT_MONO_MEDIUM_LIGHT, value)));
            }
            Some(paragraphs)
        } else {
            None
        };

        let fee_paragraphs = if let Some(items) = fee_items {
            let mut paragraphs = ParagraphVecShort::new();
            for pair in IterBuf::new().try_iterate(items)? {
                let [label, value]: [TString; 2] = util::iter_into_array(pair)?;
                unwrap!(paragraphs.push(Paragraph::new(&theme::TEXT_SMALL_LIGHT, label).no_break()));
                unwrap!(paragraphs.push(Paragraph::new(&theme::TEXT_MONO_LIGHT, value)));
            }
            Some(paragraphs)
        } else {
            None
        };

        let flow = flow::confirm_output::new_confirm_output(
            title,
            subtitle,
            chunkify,
            message,
            amount,
            br_name,
            br_code,
            account_title,
            account_paragraphs,
            address_title,
            address_paragraphs,
            summary_title,
            summary_paragraphs,
            summary_br_code,
            summary_br_name,
            fee_paragraphs,
            cancel_text,
        )?;
        Ok(flow)
    }

    fn flow_confirm_set_new_pin(
        title: TString<'static>,
        description: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let flow = flow::confirm_set_new_pin::new_set_new_pin(title, description)?;
        Ok(flow)
    }

    fn flow_get_address(
        address: Obj,
        title: TString<'static>,
        description: Option<TString<'static>>,
        extra: Option<TString<'static>>,
        chunkify: bool,
        address_qr: TString<'static>,
        case_sensitive: bool,
        account: Option<TString<'static>>,
        path: Option<TString<'static>>,
        xpubs: Obj,
        title_success: TString<'static>,
        br_code: u16,
        br_name: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let flow = flow::get_address::new_get_address(
            title,
            description,
            extra,
            address,
            chunkify,
            address_qr,
            case_sensitive,
            account,
            path,
            xpubs,
            title_success,
            br_code,
            br_name,
        )?;
        Ok(flow)
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
        title: TString<'static>,
        count: u32,
        min_count: u32,
        max_count: u32,
        description: Option<TString<'static>>,
        more_info_callback: Option<impl Fn(u32) -> TString<'static> + 'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let description = description.unwrap_or(TString::empty());

        let flow = flow::request_number::new_request_number(
            title,
            count,
            min_count,
            max_count,
            description,
            unwrap!(more_info_callback),
        )?;
        Ok(flow)
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
        let component = SelectWordScreen::new(words, description).with_header(Header::new(title));

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

    fn set_brightness(current_brightness: Option<u8>) -> Result<impl LayoutMaybeTrace, Error> {
        let content = SetBrightnessScreen::new(
            theme::backlight::get_backlight_min() as u16,
            theme::backlight::get_backlight_max() as u16,
            current_brightness.unwrap_or(theme::backlight::get_backlight_normal()) as u16,
        );
        let layout = RootComponent::new(content);
        Ok(layout)
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
        title: TString<'static>,
        button: TString<'static>,
        active: usize,
        items: [TString<'static>; MAX_CHECKLIST_ITEMS],
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let mut paragraphs = ParagraphVecShort::new();
        for (i, item) in items.into_iter().enumerate() {
            let style = match i.cmp(&active) {
                Ordering::Less => &theme::TEXT_CHECKLIST_INACTIVE,
                Ordering::Equal => &theme::TEXT_MEDIUM,
                Ordering::Greater => &theme::TEXT_CHECKLIST_INACTIVE,
            };
            paragraphs.add(Paragraph::new(style, item));
        }

        let checklist_content = Checklist::from_paragraphs(
            theme::ICON_CHEVRON_RIGHT_MINI,
            theme::ICON_CHECKMARK_MINI,
            active,
            paragraphs.into_paragraphs().with_spacing(40),
        )
        .with_check_width(32)
        .with_icon_done_color(theme::GREEN_LIGHT)
        .with_done_offset(Offset::y(7))
        .with_current_offset(Offset::y(4));

        let layout = RootComponent::new(
            TextScreen::new(checklist_content)
                .with_header(Header::new(title))
                .with_action_bar(ActionBar::new_double(
                    Button::with_icon(theme::ICON_CROSS).styled(theme::button_cancel()),
                    Button::with_text(button),
                )),
        );

        Ok(layout)
    }

    fn show_danger(
        title: TString<'static>,
        description: TString<'static>,
        value: TString<'static>,
        menu_title: Option<TString<'static>>,
        verb_cancel: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let flow =
            flow::show_danger::new_show_danger(title, description, value, menu_title, verb_cancel)?;
        Ok(flow)
    }

    fn show_error(
        title: TString<'static>,
        button: TString<'static>,
        description: TString<'static>,
        allow_cancel: bool,
        _time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error> {
        let content = Paragraphs::new(Paragraph::new(&theme::firmware::TEXT_REGULAR, description))
            .with_placement(LinearPlacement::vertical());

        let action_bar = if allow_cancel {
            ActionBar::new_double(
                Button::with_icon(theme::ICON_CLOSE),
                Button::with_text(button),
            )
        } else {
            ActionBar::new_single(Button::with_text(button))
        };
        let screen = TextScreen::new(content)
            .with_header(
                Header::new(title)
                    .with_icon(theme::ICON_WARNING, theme::ORANGE)
                    .with_text_style(theme::label_title_danger()),
            )
            .with_action_bar(action_bar);
        let obj = LayoutObj::new(screen)?;
        Ok(obj)
    }

    fn show_group_share_success(
        lines: [TString<'static>; MAX_GROUP_SHARE_LINES],
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let paragraphs = Paragraph::new(&theme::TEXT_REGULAR, lines[0])
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical());

        let layout = RootComponent::new(
            TextScreen::new(paragraphs)
                .with_header(
                    Header::new(TR::words__title_done.into())
                        .with_icon(theme::ICON_DONE, theme::GREEN_LIGHT)
                        .with_text_style(theme::label_title_confirm()),
                )
                .with_action_bar(ActionBar::new_single(Button::with_text(
                    TR::buttons__continue.into(),
                ))),
        );
        Ok(layout)
    }

    fn show_homescreen(
        label: TString<'static>,
        hold: bool,
        notification: Option<TString<'static>>,
        notification_level: u8,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let locked = false;
        let bootscreen = false;
        let coinjoin_authorized = false;
        let notification = notification.map(|w| (w, notification_level));
        let layout = RootComponent::new(Homescreen::new(
            label,
            hold,
            locked,
            bootscreen,
            coinjoin_authorized,
            notification,
        )?);
        Ok(layout)
    }

    fn show_device_menu(
        failed_backup: bool,
        battery_percentage: u8,
        firmware_version: TString<'static>,
        device_name: TString<'static>,
        paired_devices: Vec<TString<'static>, 1>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let layout = RootComponent::new(DeviceMenuScreen::new(
            failed_backup,
            battery_percentage,
            firmware_version,
            device_name,
            paired_devices,
        )?);
        Ok(layout)
    }

    fn show_pairing_device_name(
        device_name: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let font = fonts::FONT_SATOSHI_REGULAR_38;
        let text_style = theme::firmware::TEXT_REGULAR;
        let mut ops = OpTextLayout::new(text_style);
        ops = ops.color(theme::GREEN);
        ops = ops.text(device_name, font);
        ops = ops.color(text_style.text_color);
        let text: TString = " is your Trezor's name.".into();
        ops = ops.text(text, font);
        let screen = TextScreen::new(FormattedText::new(ops))
            .with_header(Header::new("Pair with new device".into()).with_close_button())
            .with_action_bar(ActionBar::new_single(Button::with_text(
                "Continue on host".into(),
            )));
        let layout = RootComponent::new(screen);
        Ok(layout)
    }

    fn show_pairing_code(code: TString<'static>) -> Result<impl LayoutMaybeTrace, Error> {
        let text: TString<'static> = "Pairing code match?".into();
        let mut ops = OpTextLayout::new(theme::firmware::TEXT_REGULAR);
        ops = ops.text(text, fonts::FONT_SATOSHI_REGULAR_38);
        ops = ops.newline().newline().newline();
        ops = ops.alignment(Alignment::Center);
        ops = ops.text(code, fonts::FONT_SATOSHI_EXTRALIGHT_72);
        let screen = TextScreen::new(FormattedText::new(ops))
            .with_header(Header::new("Bluetooth pairing".into()))
            .with_action_bar(ActionBar::new_cancel_confirm());
        let layout = RootComponent::new(screen);
        Ok(layout)
    }

    fn show_info(
        title: TString<'static>,
        description: TString<'static>,
        button: TString<'static>,
        _time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error> {
        let content = Paragraphs::new(Paragraph::new(&theme::TEXT_REGULAR, description))
            .with_placement(LinearPlacement::vertical());

        let screen = TextScreen::new(content)
            .with_header(Header::new(title))
            .with_action_bar(ActionBar::new_single(Button::with_text(button)));
        let obj = LayoutObj::new(screen)?;
        Ok(obj)
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
            paragraphs.add(Paragraph::new(&theme::TEXT_SMALL_LIGHT, key).no_break());
            if chunkify {
                paragraphs.add(Paragraph::new(
                    theme::get_chunkified_text_style(value.len()),
                    value,
                ));
            } else {
                paragraphs.add(Paragraph::new(&theme::TEXT_MONO_LIGHT, value));
            }
        }

        let screen = TextScreen::new(
            paragraphs
                .into_paragraphs()
                .with_spacing(12)
                .with_placement(LinearPlacement::vertical()),
        )
        .with_header(Header::new(title).with_close_button());
        let layout = RootComponent::new(screen);
        Ok(layout)
    }

    fn show_lockscreen(
        label: TString<'static>,
        bootscreen: bool,
        coinjoin_authorized: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let locked = true;
        let notification = None;
        let hold = false;
        let layout = RootComponent::new(Homescreen::new(
            label,
            hold,
            locked,
            bootscreen,
            coinjoin_authorized,
            notification,
        )?);
        Ok(layout)
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
        indeterminate: bool,
        title: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let (title, description) = if let Some(title) = title {
            (title, description)
        } else {
            (description, "".into())
        };

        let layout = RootComponent::new(ProgressScreen::new_progress(
            title,
            indeterminate,
            description,
        ));
        Ok(layout)
    }

    fn show_progress_coinjoin(
        description: TString<'static>,
        indeterminate: bool,
        time_ms: u32,
        skip_first_paint: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        let progress = ProgressScreen::new_coinjoin_progress(
            TR::coinjoin__title_progress.into(),
            indeterminate,
            description,
        );
        let obj = if time_ms > 0 && indeterminate {
            let timeout = Timeout::new(time_ms);
            LayoutObj::new((timeout, progress.map(|_msg| None)))?
        } else {
            LayoutObj::new(progress)?
        };
        if skip_first_paint {
            obj.skip_first_paint();
        }
        Ok(obj)
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
        let mut instructions_paragraphs = ParagraphVecShort::new();
        for item in IterBuf::new().try_iterate(instructions)? {
            let text: TString = item.try_into()?;
            instructions_paragraphs.add(Paragraph::new(&theme::TEXT_REGULAR, text));
        }

        let flow = flow::show_share_words::new_show_share_words_flow(
            words,
            subtitle.unwrap_or(TString::empty()),
            instructions_paragraphs,
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
        time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error> {
        let paragraphs = Paragraph::new(&theme::TEXT_REGULAR, description)
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical());
        let header = Header::new(title)
            .with_icon(theme::ICON_DONE, theme::GREEN_LIGHT)
            .with_text_style(theme::label_title_confirm());
        let action_bar = if allow_cancel {
            ActionBar::new_double(
                Button::with_icon(theme::ICON_CROSS),
                Button::with_text(button),
            )
        } else if time_ms > 0 {
            ActionBar::new_timeout(Button::with_text(button), time_ms)
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
        danger: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        let paragraphs = ParagraphVecShort::from_iter([
            Paragraph::new(&theme::TEXT_SMALL, description),
            Paragraph::new(&theme::TEXT_REGULAR, value),
        ])
        .into_paragraphs()
        .with_placement(LinearPlacement::vertical());

        let (color, style) = if danger {
            (theme::ORANGE, theme::label_title_danger())
        } else {
            (theme::YELLOW, theme::label_title_warning())
        };

        let header = Header::new(title)
            .with_icon(theme::ICON_INFO, color)
            .with_text_style(style);
        let action_bar = if allow_cancel {
            ActionBar::new_double(
                Button::with_icon(theme::ICON_CROSS).styled(theme::button_cancel()),
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
