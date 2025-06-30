use core::cmp::Ordering;

use crate::{
    error::Error,
    io::BinaryData,
    micropython::{gc::Gc, iter::IterBuf, list::List, obj::Obj, util},
    strutil::TString,
    time::Duration,
    translations::TR,
    ui::{
        component::{
            text::{
                op::OpTextLayout,
                paragraphs::{
                    Checklist, Paragraph, ParagraphSource, ParagraphVecShort, Paragraphs, VecExt,
                },
                TextStyle,
            },
            ComponentExt as _, Empty, FormattedText, Timeout,
        },
        geometry::{Alignment, LinearPlacement, Offset},
        layout::{
            obj::{LayoutMaybeTrace, LayoutObj, RootComponent},
            util::{ConfirmValueParams, ContentType, PropsList, RecoveryType, StrOrBytes},
        },
        ui_firmware::{
            FirmwareUI, ERROR_NOT_IMPLEMENTED, MAX_CHECKLIST_ITEMS, MAX_GROUP_SHARE_LINES,
            MAX_WORD_QUIZ_ITEMS,
        },
        ModelUI,
    },
};

use super::{
    component::Button,
    firmware::{
        ActionBar, Bip39Input, ConfirmHomescreen, DeviceMenuScreen, DurationInput, Header,
        HeaderMsg, Hint, Homescreen, MnemonicKeyboard, PinKeyboard, ProgressScreen,
        SelectWordCountScreen, SelectWordScreen, SetBrightnessScreen, Slip39Input, TextScreen,
        ValueInputScreen,
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
        hold_danger: bool,
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

        let right_button = if hold {
            let verb = verb.unwrap_or(TR::buttons__hold_to_confirm.into());
            let style = if hold_danger {
                theme::firmware::button_actionbar_danger()
            } else {
                theme::firmware::button_confirm()
            };
            Button::with_text(verb)
                .with_long_press(theme::CONFIRM_HOLD_DURATION)
                .with_long_press_danger(hold_danger)
                .styled(style)
        } else if let Some(verb) = verb {
            Button::with_text(verb)
        } else {
            Button::with_text(TR::buttons__confirm.into()).styled(theme::firmware::button_confirm())
        };

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
        Err::<Gc<LayoutObj>, Error>(ERROR_NOT_IMPLEMENTED)
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
                ops.add_text(TString::try_from(item)?, font);
            } else {
                let [emphasis, text]: [Obj; 2] = util::iter_into_array(item)?;
                let text: TString = text.try_into()?;
                if emphasis.try_into()? {
                    ops.add_color(theme::WHITE)
                        .add_text(text, font)
                        .add_color(text_style.text_color);
                } else {
                    ops.add_text(text, font);
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
        description: TString<'static>,
        fingerprint: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let flow =
            flow::confirm_firmware_update::new_confirm_firmware_update(description, fingerprint)?;
        Ok(flow)
    }

    fn confirm_modify_fee(
        title: TString<'static>,
        sign: i32,
        user_fee_change: TString<'static>,
        total_fee_new: TString<'static>,
        _fee_rate_amount: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let (description, change, total_label, info_hint) = match sign {
            s if s < 0 => (
                Some(TR::modify_fee__decrease_fee),
                user_fee_change,
                TR::modify_fee__new_transaction_fee,
                None,
            ),
            s if s > 0 => (
                Some(TR::modify_fee__increase_fee),
                user_fee_change,
                TR::modify_fee__new_transaction_fee,
                None,
            ),
            _ => (
                None,
                TString::empty(),
                TR::modify_fee__transaction_fee,
                Some(TR::modify_fee__no_change.into()),
            ),
        };

        let mut paragraphs = ParagraphVecShort::new();
        if let Some(description) = description {
            paragraphs
                .add(
                    Paragraph::new(&theme::TEXT_SMALL_LIGHT, description)
                        .with_bottom_padding(theme::PARAGRAPHS_SPACING),
                )
                .add(Paragraph::new(&theme::TEXT_MONO_EXTRA_LIGHT, change).with_bottom_padding(16));
        }
        paragraphs
            .add(
                Paragraph::new(&theme::TEXT_SMALL_LIGHT, total_label)
                    .with_bottom_padding(theme::PARAGRAPHS_SPACING),
            )
            .add(Paragraph::new(&theme::TEXT_MONO_EXTRA_LIGHT, total_fee_new));

        let flow = flow::new_confirm_with_menu(
            title,
            None,
            paragraphs
                .into_paragraphs()
                .with_placement(LinearPlacement::vertical()),
            info_hint,
            None,
            false,
            Some(TR::confirm_total__title_fee.into()),
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
            Paragraph::new(&theme::TEXT_MONO_EXTRA_LIGHT, amount_change),
            Paragraph::new(&theme::TEXT_SMALL_LIGHT, TR::modify_amount__new_amount),
            Paragraph::new(&theme::TEXT_MONO_EXTRA_LIGHT, amount_new),
        ]);

        let layout = RootComponent::new(
            TextScreen::new(paragraphs.into_paragraphs().with_placement(
                LinearPlacement::vertical().with_spacing(theme::PARAGRAPHS_SPACING),
            ))
            .with_header(Header::new(TR::modify_amount__title.into()))
            .with_action_bar(ActionBar::new_cancel_confirm()),
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
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
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
                paragraphs
                    .add(Paragraph::new(&theme::TEXT_SMALL_LIGHT, label).no_break())
                    .add(Paragraph::new(&theme::TEXT_MONO_LIGHT, value));
            }
            Some(paragraphs)
        } else {
            None
        };
        let extra_paragraphs = if let Some(items) = extra_items {
            let mut paragraphs = ParagraphVecShort::new();
            for pair in IterBuf::new().try_iterate(items)? {
                let [label, value]: [TString; 2] = util::iter_into_array(pair)?;
                paragraphs
                    .add(Paragraph::new(&theme::TEXT_SMALL_LIGHT, label).no_break())
                    .add(Paragraph::new(&theme::TEXT_MONO_LIGHT, value));
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
        _subtitle: Option<TString<'static>>,
        items: Obj,
        hold: bool,
        verb: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let paragraphs = PropsList::new(
            items,
            &theme::TEXT_SMALL_LIGHT,
            &theme::TEXT_MONO_MEDIUM_LIGHT,
            &theme::TEXT_MONO_MEDIUM_LIGHT_DATA,
        )?;

        let flow = flow::new_confirm_with_menu(
            title,
            None,
            paragraphs.into_paragraphs().with_placement(
                LinearPlacement::vertical().with_spacing(theme::PARAGRAPHS_SPACING),
            ),
            None,
            verb,
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
        subtitle: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        _verb_cancel: Option<TString<'static>>,
        info: bool,
        hold: bool,
        chunkify: bool,
        page_counter: bool,
        _prompt_screen: bool,
        cancel: bool,
        warning_footer: Option<TString<'static>>,
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
                &theme::TEXT_MONO_ADDRESS
            } else {
                &theme::TEXT_MEDIUM
            },
            description_font: &theme::TEXT_SMALL,
            extra_font: &theme::TEXT_SMALL,
        }
        .into_paragraphs()
        .with_placement(LinearPlacement::vertical());

        let mut right_button = if hold {
            let verb = verb.unwrap_or(TR::buttons__hold_to_confirm.into());
            Button::with_text(verb)
                .with_long_press(theme::CONFIRM_HOLD_DURATION)
                .styled(theme::firmware::button_confirm())
        } else if let Some(verb) = verb {
            Button::with_text(verb)
        } else {
            Button::with_text(TR::buttons__confirm.into()).styled(theme::firmware::button_confirm())
        };
        if warning_footer.is_some() {
            right_button = right_button.styled(theme::button_cancel_gradient());
        }
        let header = if info {
            Header::new(title)
                .with_right_button(Button::with_icon(theme::ICON_INFO), HeaderMsg::Menu)
        } else {
            Header::new(title)
        };

        let action_bar = if cancel {
            ActionBar::new_double(Button::with_icon(theme::ICON_CROSS), right_button)
        } else {
            ActionBar::new_single(right_button)
        };

        let mut screen = TextScreen::new(paragraphs)
            .with_header(header)
            .with_subtitle(subtitle.unwrap_or(TString::empty()))
            .with_action_bar(action_bar);
        if page_counter {
            screen = screen.with_hint(Hint::new_page_counter());
        }
        if let Some(warning_footer) = warning_footer {
            screen = screen.with_hint(Hint::new_warning_caution(warning_footer));
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
        subtitle: Option<TString<'static>>,
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
                &theme::TEXT_MONO_LIGHT
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
            subtitle,
            paragraphs
                .into_paragraphs()
                .with_placement(LinearPlacement::vertical())
                .with_spacing(12),
            None,
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
        let shares_layout = if let Some(pages_obj) = remaining_shares {
            let mut op_layout = OpTextLayout::new(theme::TEXT_SMALL);
            let mut iter_buf = IterBuf::new();
            let mut n_pages = 0;
            for page in iter_buf.try_iterate(pages_obj)? {
                if n_pages > 0 {
                    op_layout.add_next_page();
                }
                n_pages += 1;
                let [title, description]: [TString; 2] = util::iter_into_array(page)?;
                op_layout
                    .add_line_spacing(3)
                    .add_color(theme::GREY_EXTRA_LIGHT)
                    .add_text(title, fonts::FONT_SATOSHI_MEDIUM_26)
                    .add_newline()
                    .add_offset(Offset::y(24))
                    .add_color(theme::GREY_LIGHT)
                    .add_line_spacing(16)
                    .add_text(description, fonts::FONT_MONO_MEDIUM_38);
            }

            Some((op_layout, n_pages))
        } else {
            None
        };

        let flow = flow::continue_recovery_homepage::new_continue_recovery_homepage(
            text,
            subtext,
            recovery_type,
            show_instructions,
            shares_layout,
        )?;
        LayoutObj::new_root(flow)
    }

    fn flow_confirm_output(
        title: Option<TString<'static>>,
        subtitle: Option<TString<'static>>,
        description: Option<TString<'static>>,
        extra: Option<TString<'static>>,
        message: Obj,
        amount: Option<Obj>,
        chunkify: bool,
        text_mono: bool,
        account_title: TString<'static>,
        account: Option<TString<'static>>,
        account_path: Option<TString<'static>>,
        br_code: u16,
        br_name: TString<'static>,
        address_item: Option<(TString<'static>, Obj)>,
        extra_item: Option<(TString<'static>, Obj)>,
        summary_items: Option<Obj>,
        fee_items: Option<Obj>,
        summary_title: Option<TString<'static>>,
        summary_br_code: Option<u16>,
        summary_br_name: Option<TString<'static>>,
        cancel_text: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let mut main_paragraphs = ParagraphVecShort::new();
        if let Some(description) = description {
            main_paragraphs.add(Paragraph::new(&theme::TEXT_REGULAR, description));
        }
        if let Some(extra) = extra {
            main_paragraphs.add(Paragraph::new(&theme::TEXT_SMALL, extra));
        }
        let font = if chunkify {
            &theme::TEXT_MONO_ADDRESS_CHUNKS
        } else if text_mono {
            &theme::TEXT_MONO_LIGHT
        } else {
            &theme::TEXT_REGULAR
        };
        main_paragraphs.add(Paragraph::new(
            font,
            message.try_into().unwrap_or(TString::empty()),
        ));

        let (address_title, address_paragraph) = if let Some((title, item)) = address_item {
            let paragraph = Paragraph::new(
                &theme::TEXT_MONO_ADDRESS_CHUNKS,
                item.try_into().unwrap_or(TString::empty()),
            );
            (Some(title), Some(paragraph))
        } else {
            (None, None)
        };

        // collect available info
        let account_paragraphs = {
            let mut paragraphs = ParagraphVecShort::new();
            if let Some(account) = account {
                paragraphs
                    .add(
                        Paragraph::new(
                            &theme::TEXT_SMALL_LIGHT,
                            TString::from_translation(TR::words__wallet),
                        )
                        .no_break(),
                    )
                    .add(Paragraph::new(&theme::TEXT_MONO_LIGHT, account));
            }
            if let Some(path) = account_path {
                paragraphs
                    .add(
                        Paragraph::new(
                            &theme::TEXT_SMALL_LIGHT,
                            TString::from_translation(TR::address_details__derivation_path),
                        )
                        .no_break(),
                    )
                    .add(Paragraph::new(&theme::TEXT_MONO_LIGHT, path));
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
                paragraphs
                    .add(Paragraph::new(&theme::TEXT_SMALL_LIGHT, label).no_break())
                    .add(Paragraph::new(&theme::TEXT_MONO_MEDIUM_LIGHT, value));
            }
            Some(paragraphs)
        } else {
            None
        };

        let fee_paragraphs = if let Some(items) = fee_items {
            let mut paragraphs = ParagraphVecShort::new();
            for pair in IterBuf::new().try_iterate(items)? {
                let [label, value]: [TString; 2] = util::iter_into_array(pair)?;
                paragraphs
                    .add(Paragraph::new(&theme::TEXT_SMALL_LIGHT, label).no_break())
                    .add(Paragraph::new(&theme::TEXT_MONO_MEDIUM_LIGHT, value));
            }
            Some(paragraphs)
        } else {
            None
        };

        let (extra_title, extra_paragraph) = if let Some((title, item)) = extra_item {
            let paragraph = Paragraph::new(
                &theme::TEXT_MONO_ADDRESS,
                item.try_into().unwrap_or(TString::empty()),
            );
            (Some(title), Some(paragraph))
        } else {
            (None, None)
        };

        let flow = flow::confirm_output::new_confirm_output(
            title,
            subtitle,
            main_paragraphs,
            amount,
            br_name,
            br_code,
            account_title,
            account_paragraphs,
            address_title,
            address_paragraph,
            summary_title,
            summary_paragraphs,
            summary_br_code,
            summary_br_name,
            extra_title,
            extra_paragraph,
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
        address: TString<'static>,
        title: TString<'static>,
        subtitle: Option<TString<'static>>,
        description: Option<TString<'static>>,
        hint: Option<TString<'static>>,
        chunkify: bool,
        address_qr: TString<'static>,
        case_sensitive: bool,
        account: Option<TString<'static>>,
        path: Option<TString<'static>>,
        xpubs: Obj,
        br_code: u16,
        br_name: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let flow = flow::receive::new_receive(
            title,
            subtitle,
            description,
            hint,
            ContentType::Address(address),
            chunkify,
            address_qr,
            case_sensitive,
            account,
            path,
            xpubs,
            br_code,
            br_name,
        )?;
        Ok(flow)
    }

    fn flow_get_pubkey(
        pubkey: TString<'static>,
        title: TString<'static>,
        subtitle: Option<TString<'static>>,
        hint: Option<TString<'static>>,
        pubkey_qr: TString<'static>,
        account: Option<TString<'static>>,
        path: Option<TString<'static>>,
        br_code: u16,
        br_name: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let flow = flow::receive::new_receive(
            title,
            subtitle,
            None,
            hint,
            ContentType::PublicKey(pubkey),
            false,
            pubkey_qr,
            true,
            account,
            path,
            Obj::const_none(),
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
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
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

    fn request_duration(
        title: TString<'static>,
        duration_ms: u32,
        min_ms: u32,
        max_ms: u32,
        description: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let description = description.unwrap_or(TString::empty());
        let component = ValueInputScreen::new(
            DurationInput::new(
                Duration::from_millis(min_ms),
                Duration::from_millis(max_ms),
                Duration::from_millis(duration_ms),
            ),
            description,
        )
        .with_header(Header::new(title));

        let layout = RootComponent::new(component);

        Ok(layout)
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
        let title = match recovery_type {
            RecoveryType::DryRun => TR::reset__check_wallet_backup_title,
            RecoveryType::Normal | RecoveryType::UnlockRepeatedBackup => {
                TR::recovery__title_recover
            }
        };
        let content = if matches!(recovery_type, RecoveryType::UnlockRepeatedBackup) {
            SelectWordCountScreen::new_multi_share(description)
        } else {
            SelectWordCountScreen::new_single_share(description)
        }
        .with_header(Header::new(title.into()));
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
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
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
            paragraphs
                .into_paragraphs()
                .with_placement(LinearPlacement::vertical().with_spacing(40)),
        )
        .with_check_width(32)
        .with_icon_done_color(theme::GREEN_LIGHT)
        .with_done_offset(Offset::y(7))
        .with_current_offset(Offset::y(4));

        let layout = RootComponent::new(
            TextScreen::new(checklist_content)
                .with_header(Header::new(title))
                .with_action_bar(ActionBar::new_double(
                    Button::with_icon(theme::ICON_CROSS),
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
        notification: Option<TString<'static>>,
        notification_level: u8,
        lockable: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let locked = false;
        let bootscreen = false;
        let coinjoin_authorized = false;
        let notification = notification.map(|w| (w, notification_level));
        let layout = RootComponent::new(Homescreen::new(
            label,
            lockable,
            locked,
            bootscreen,
            coinjoin_authorized,
            notification,
        )?);
        Ok(layout)
    }

    fn show_device_menu(
        failed_backup: bool,
        firmware_version: TString<'static>,
        device_name: TString<'static>,
        paired_devices: Vec<TString<'static>, 1>,
        auto_lock_delay: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let layout = RootComponent::new(DeviceMenuScreen::new(
            failed_backup,
            firmware_version,
            device_name,
            paired_devices,
            auto_lock_delay,
        )?);
        Ok(layout)
    }

    fn show_pairing_device_name(
        device_name: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let font = fonts::FONT_SATOSHI_REGULAR_38;
        let text_style = theme::firmware::TEXT_REGULAR;
        let mut ops = OpTextLayout::new(text_style);
        let text: TString = " is your Trezor's name.".into();
        ops.add_color(theme::GREEN)
            .add_text(device_name, font)
            .add_color(text_style.text_color)
            .add_text(text, font);
        let screen = TextScreen::new(FormattedText::new(ops))
            .with_header(Header::new("Pair with new device".into()).with_close_button())
            .with_action_bar(ActionBar::new_text_only("Continue on host".into()));
        #[cfg(feature = "ble")]
        let screen = crate::ui::component::BLEHandler::new(screen, true);
        let layout = RootComponent::new(screen);
        Ok(layout)
    }

    #[cfg(feature = "ble")]
    fn show_ble_pairing_code(
        title: TString<'static>,
        description: TString<'static>,
        code: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let mut ops = OpTextLayout::new(theme::firmware::TEXT_REGULAR);
        ops.add_text(description, fonts::FONT_SATOSHI_REGULAR_38)
            .add_newline()
            .add_newline()
            .add_newline()
            .add_alignment(Alignment::Center)
            .add_text(code, fonts::FONT_SATOSHI_EXTRALIGHT_72);
        let screen = crate::ui::component::BLEHandler::new(
            TextScreen::new(FormattedText::new(ops))
                .with_header(Header::new(title))
                .with_action_bar(ActionBar::new_cancel_confirm()),
            false,
        );
        let layout = RootComponent::new(screen);
        Ok(layout)
    }

    fn show_thp_pairing_code(
        title: TString<'static>,
        description: TString<'static>,
        code: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let flow =
            flow::show_thp_pairing_code::new_show_thp_pairing_code(title, description, code)?;
        Ok(flow)
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

        let screen =
            TextScreen::new(paragraphs.into_paragraphs().with_placement(
                LinearPlacement::vertical().with_spacing(theme::PARAGRAPHS_SPACING),
            ))
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

        let text_style = theme::TEXT_REGULAR;
        let mut ops = OpTextLayout::new(text_style);
        ops.add_text(description, text_style.text_font)
            .add_text(url, theme::TEXT_MONO_MEDIUM.text_font);

        let screen = TextScreen::new(FormattedText::new(ops))
            .with_header(Header::new(title))
            .with_action_bar(ActionBar::new_double(
                Button::with_icon(theme::ICON_CROSS),
                Button::with_text(button),
            ));

        let layout = RootComponent::new(screen);
        Ok(layout)
    }

    fn show_progress(
        description: TString<'static>,
        indeterminate: bool,
        title: Option<TString<'static>>,
        danger: bool,
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
            danger,
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
        instructions_verb: Option<TString<'static>>,
        // Irrelevant for Eckhart because the footer is dynamic
        _text_footer: Option<TString<'static>>,
        text_confirm: TString<'static>,
        text_check: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let instructions_paragraphs = {
            let mut vec = ParagraphVecShort::new();
            for item in IterBuf::new().try_iterate(instructions)? {
                let text: TString = item.try_into()?;
                vec.add(Paragraph::new(&theme::TEXT_REGULAR, text));
            }
            match vec.is_empty() {
                true => None,
                false => Some(vec),
            }
        };

        let flow = flow::show_share_words::new_show_share_words_flow(
            words,
            subtitle.unwrap_or(TString::empty()),
            instructions_paragraphs,
            instructions_verb,
            text_confirm,
            text_check,
        )?;
        Ok(flow)
    }

    fn show_remaining_shares(_pages_iterable: Obj) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
    }

    fn show_simple(
        text: TString<'static>,
        title: Option<TString<'static>>,
        button: Option<TString<'static>>,
    ) -> Result<Gc<LayoutObj>, Error> {
        let paragraphs = Paragraph::new(&theme::TEXT_REGULAR, text)
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical());

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
            Paragraph::new(&theme::TEXT_REGULAR, description),
            Paragraph::new(&theme::TEXT_REGULAR, value),
        ])
        .into_paragraphs()
        .with_placement(LinearPlacement::vertical())
        .with_spacing(theme::TEXT_VERTICAL_SPACING);

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
                Button::with_icon(theme::ICON_CROSS),
                Button::with_single_line_text(button),
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
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
    }
}
