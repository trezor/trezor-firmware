use core::cmp::Ordering;

use crate::{
    error::{value_error, Error},
    io::BinaryData,
    micropython::{gc::Gc, iter::IterBuf, list::List, obj::Obj, util},
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            connect::Connect,
            swipe_detect::SwipeSettings,
            text::{
                op::OpTextLayout,
                paragraphs::{
                    Checklist, Paragraph, ParagraphSource, ParagraphVecLong, ParagraphVecShort,
                    Paragraphs, VecExt,
                },
                TextStyle,
            },
            Border, CachedJpeg, ComponentExt, Empty, FormattedText, Never, Timeout,
        },
        geometry::{self, Direction},
        layout::{
            obj::{LayoutMaybeTrace, LayoutObj, RootComponent},
            util::{PropsList, RecoveryType},
        },
        ui_firmware::{
            FirmwareUI, MAX_CHECKLIST_ITEMS, MAX_GROUP_SHARE_LINES, MAX_WORD_QUIZ_ITEMS,
        },
        ModelUI,
    },
};

use super::{
    component::{
        check_homescreen_format, Bip39Input, CoinJoinProgress, Frame, Homescreen, Lockscreen,
        MnemonicKeyboard, PinKeyboard, Progress, SelectWordCount, Slip39Input, StatusScreen,
        SwipeContent, SwipeUpScreen, VerticalMenu,
    },
    flow::{
        self, new_confirm_action_simple, ConfirmActionExtra, ConfirmActionMenuStrings,
        ConfirmActionStrings, ConfirmBlobParams, ShowInfoParams,
    },
    theme, UIMercury,
};

impl FirmwareUI for UIMercury {
    fn confirm_action(
        title: TString<'static>,
        action: Option<TString<'static>>,
        description: Option<TString<'static>>,
        subtitle: Option<TString<'static>>,
        _verb: Option<TString<'static>>,
        verb_cancel: Option<TString<'static>>,
        hold: bool,
        _hold_danger: bool,
        reverse: bool,
        prompt_screen: bool,
        prompt_title: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let flow = flow::confirm_action::new_confirm_action(
            title,
            action,
            description,
            subtitle,
            verb_cancel,
            reverse,
            hold,
            prompt_screen,
            prompt_title.unwrap_or(TString::empty()),
        )?;
        Ok(flow)
    }

    fn confirm_address(
        _title: TString<'static>,
        _address: Obj,
        _address_label: Option<TString<'static>>,
        _verb: Option<TString<'static>>,
        _info_button: bool,
        _chunkify: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        // confirm_value is used instead
        Err::<Gc<LayoutObj>, Error>(Error::ValueError(c"confirm_address not implemented"))
    }

    fn confirm_blob(
        title: TString<'static>,
        data: Obj,
        description: Option<TString<'static>>,
        text_mono: bool,
        extra: Option<TString<'static>>,
        subtitle: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        verb_cancel: Option<TString<'static>>,
        verb_info: Option<TString<'static>>,
        info: bool,
        hold: bool,
        chunkify: bool,
        page_counter: bool,
        prompt_screen: bool,
        cancel: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        ConfirmBlobParams::new(title, data, description)
            .with_description_font(&theme::TEXT_SUB_GREY)
            .with_text_mono(text_mono)
            .with_subtitle(subtitle)
            .with_verb(verb)
            .with_verb_cancel(verb_cancel)
            .with_verb_info(if info {
                Some(verb_info.unwrap_or(TR::words__title_information.into()))
            } else {
                None
            })
            .with_extra(extra)
            .with_chunkify(chunkify)
            .with_page_counter(page_counter)
            .with_cancel(cancel)
            .with_prompt(prompt_screen)
            .with_hold(hold)
            .into_flow()
            .and_then(LayoutObj::new_root)
            .map(Into::into)
    }

    fn confirm_blob_intro(
        title: TString<'static>,
        data: Obj,
        subtitle: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        verb_cancel: Option<TString<'static>>,
        chunkify: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        const CONFIRM_BLOB_INTRO_MARGIN: usize = 24;
        ConfirmBlobParams::new(title, data, Some(TR::instructions__view_all_data.into()))
            .with_verb(verb)
            .with_verb_info(Some(TR::buttons__view_all_data.into()))
            .with_description_font(&theme::TEXT_SUB_GREEN_LIME)
            .with_subtitle(subtitle)
            .with_verb_cancel(verb_cancel)
            .with_footer_description(Some(
                TR::buttons__confirm.into(), /* or words__confirm?? */
            ))
            .with_chunkify(chunkify)
            .with_page_limit(Some(1))
            .with_frame_margin(CONFIRM_BLOB_INTRO_MARGIN)
            .into_flow()
            .and_then(LayoutObj::new_root)
            .map(Into::into)
    }

    fn confirm_homescreen(
        title: TString<'static>,
        image: BinaryData<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let layout = if image.is_empty() {
            // Incoming data may be empty, meaning we should
            // display default homescreen message.
            let paragraphs = ParagraphVecShort::from_iter([Paragraph::new(
                &theme::TEXT_DEMIBOLD,
                TR::homescreen__set_default,
            )])
            .into_paragraphs();

            new_confirm_action_simple(
                paragraphs,
                ConfirmActionExtra::Menu(ConfirmActionMenuStrings::new()),
                ConfirmActionStrings::new(
                    TR::homescreen__settings_title.into(),
                    Some(TR::homescreen__settings_subtitle.into()),
                    None,
                    Some(TR::homescreen__settings_title.into()),
                ),
                false,
                None,
                0,
                false,
            )?
        } else {
            if !check_homescreen_format(image) {
                return Err(value_error!(c"Invalid image."));
            };

            flow::confirm_homescreen::new_confirm_homescreen(title, CachedJpeg::new(image, 1)?)?
        };
        Ok(layout)
    }

    fn confirm_coinjoin(
        max_rounds: TString<'static>,
        max_feerate: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let paragraphs = ParagraphVecShort::from_iter([
            Paragraph::new(&theme::TEXT_NORMAL, TR::coinjoin__max_rounds),
            Paragraph::new(&theme::TEXT_MONO, max_rounds),
            Paragraph::new(&theme::TEXT_NORMAL, TR::coinjoin__max_mining_fee),
            Paragraph::new(&theme::TEXT_MONO, max_feerate),
        ])
        .into_paragraphs();

        let flow = flow::new_confirm_action_simple(
            paragraphs,
            ConfirmActionExtra::Menu(ConfirmActionMenuStrings::new()),
            ConfirmActionStrings::new(
                TR::coinjoin__title.into(),
                None,
                None,
                Some(TR::coinjoin__title.into()),
            ),
            true,
            None,
            0,
            false,
        )?;
        Ok(flow)
    }

    fn confirm_emphasized(
        title: TString<'static>,
        items: Obj,
        _verb: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let mut ops = OpTextLayout::new(theme::TEXT_NORMAL);
        for item in IterBuf::new().try_iterate(items)? {
            if item.is_str() {
                ops = ops.text_normal(TString::try_from(item)?)
            } else {
                let [emphasis, text]: [Obj; 2] = util::iter_into_array(item)?;
                let text: TString = text.try_into()?;
                if emphasis.try_into()? {
                    ops = ops.text_demibold(text);
                } else {
                    ops = ops.text_normal(text);
                }
            }
        }

        let flow = flow::new_confirm_action_simple(
            FormattedText::new(ops).vertically_centered(),
            ConfirmActionExtra::Menu(ConfirmActionMenuStrings::new()),
            ConfirmActionStrings::new(title, None, None, Some(title)),
            false,
            None,
            0,
            false,
        )?;
        Ok(flow)
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
            Paragraph::new(&theme::TEXT_SUB_GREY, description),
            Paragraph::new(&theme::TEXT_MONO, change),
            Paragraph::new(&theme::TEXT_SUB_GREY, total_label),
            Paragraph::new(&theme::TEXT_MONO, total_fee_new),
        ]);

        let flow = flow::new_confirm_action_simple(
            paragraphs.into_paragraphs(),
            ConfirmActionExtra::Menu(
                ConfirmActionMenuStrings::new()
                    .with_verb_info(Some(TR::words__title_information.into())),
            ),
            ConfirmActionStrings::new(title, None, None, Some(title)),
            true,
            None,
            0,
            false,
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
            Paragraph::new(&theme::TEXT_SUB_GREY, description),
            Paragraph::new(&theme::TEXT_MONO, amount_change),
            Paragraph::new(&theme::TEXT_SUB_GREY, TR::modify_amount__new_amount),
            Paragraph::new(&theme::TEXT_MONO, amount_new),
        ])
        .into_paragraphs();

        let layout = RootComponent::new(SwipeUpScreen::new(
            Frame::left_aligned(TR::modify_amount__title.into(), paragraphs)
                .with_cancel_button()
                .with_footer(TR::instructions__swipe_up.into(), None)
                .with_swipe(Direction::Up, SwipeSettings::default()),
        ));
        Ok(layout)
    }

    fn confirm_more(
        _title: TString<'static>,
        _button: TString<'static>,
        _button_style_confirm: bool,
        _items: Obj,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(
            c"confirm_more not implemented",
        ))
    }

    fn confirm_reset_device(recovery: bool) -> Result<impl LayoutMaybeTrace, Error> {
        let flow = flow::confirm_reset::new_confirm_reset(recovery)?;
        Ok(flow)
    }

    fn confirm_summary(
        amount: TString<'static>,
        amount_label: TString<'static>,
        fee: TString<'static>,
        fee_label: TString<'static>,
        title: Option<TString<'static>>,
        account_items: Option<Obj>,
        extra_items: Option<Obj>,
        extra_title: Option<TString<'static>>,
        verb_cancel: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let mut summary_params = ShowInfoParams::new(title.unwrap_or(TString::empty()))
            .with_menu_button()
            .with_footer(TR::instructions__swipe_up.into(), None)
            .with_swipe_up();
        summary_params = unwrap!(summary_params.add(amount_label, amount));
        summary_params = unwrap!(summary_params.add(fee_label, fee));

        // collect available info
        let account_params = if let Some(items) = account_items {
            let mut account_params =
                ShowInfoParams::new(TR::send__send_from.into()).with_cancel_button();
            for pair in IterBuf::new().try_iterate(items)? {
                let [label, value]: [TString; 2] = util::iter_into_array(pair)?;
                account_params = unwrap!(account_params.add(label, value));
            }
            Some(account_params)
        } else {
            None
        };
        let extra_params = if let Some(items) = extra_items {
            let extra_title = extra_title.unwrap_or(TR::buttons__more_info.into());
            let mut extra_params = ShowInfoParams::new(extra_title).with_cancel_button();
            for pair in IterBuf::new().try_iterate(items)? {
                let [label, value]: [TString; 2] = util::iter_into_array(pair)?;
                extra_params = unwrap!(extra_params.add(label, value));
            }
            Some(extra_params)
        } else {
            None
        };

        let flow = flow::new_confirm_summary(
            summary_params,
            account_params,
            extra_params,
            extra_title,
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
            &theme::TEXT_NORMAL,
            &theme::TEXT_MONO,
            &theme::TEXT_MONO,
        )?;

        let flow = flow::new_confirm_action_simple(
            paragraphs.into_paragraphs(),
            ConfirmActionExtra::Menu(ConfirmActionMenuStrings::new()),
            ConfirmActionStrings::new(title, None, None, hold.then_some(title)),
            hold,
            None,
            0,
            false,
        )?;
        Ok(flow)
    }

    fn confirm_value(
        title: TString<'static>,
        value: Obj,
        description: Option<TString<'static>>,
        subtitle: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        verb_info: Option<TString<'static>>,
        verb_cancel: Option<TString<'static>>,
        info_button: bool,
        hold: bool,
        chunkify: bool,
        text_mono: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        ConfirmBlobParams::new(title, value, description)
            .with_subtitle(subtitle)
            .with_verb(verb)
            .with_verb_cancel(verb_cancel)
            .with_verb_info(if info_button {
                Some(verb_info.unwrap_or(TR::words__title_information.into()))
            } else {
                None
            })
            .with_chunkify(chunkify)
            .with_text_mono(text_mono)
            .with_prompt(hold)
            .with_hold(hold)
            .into_flow()
            .and_then(LayoutObj::new_root)
            .map(Into::into)
    }

    fn confirm_with_info(
        title: TString<'static>,
        button: TString<'static>,
        info_button: TString<'static>,
        _verb_cancel: Option<TString<'static>>,
        items: Obj,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let mut paragraphs = ParagraphVecShort::new();

        for para in IterBuf::new().try_iterate(items)? {
            let [font, text]: [Obj; 2] = util::iter_into_array(para)?;
            let style: &TextStyle = theme::textstyle_number(font.try_into()?);
            let text: TString = text.try_into()?;
            paragraphs.add(Paragraph::new(style, text));
            if paragraphs.is_full() {
                break;
            }
        }

        let flow = flow::new_confirm_action_simple(
            paragraphs.into_paragraphs(),
            ConfirmActionExtra::Menu(
                ConfirmActionMenuStrings::new().with_verb_info(Some(info_button)),
            ),
            ConfirmActionStrings::new(title, None, None, None)
                .with_footer_description(Some(button)),
            false,
            None,
            0,
            false,
        )?;
        Ok(flow)
    }

    fn check_homescreen_format(image: BinaryData, __accept_toif: bool) -> bool {
        super::component::check_homescreen_format(image)
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
                vec.add(Paragraph::new(&theme::TEXT_SUB_GREY, title))
                    .add(Paragraph::new(&theme::TEXT_MONO_GREY_LIGHT, description).break_after());
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
        message: Obj,
        amount: Option<Obj>,
        chunkify: bool,
        text_mono: bool,
        account: Option<TString<'static>>,
        account_path: Option<TString<'static>>,
        br_code: u16,
        br_name: TString<'static>,
        address: Option<Obj>,
        address_title: Option<TString<'static>>,
        summary_items: Option<Obj>,
        fee_items: Option<Obj>,
        summary_title: Option<TString<'static>>,
        summary_br_code: Option<u16>,
        summary_br_name: Option<TString<'static>>,
        cancel_text: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let address_title = address_title.unwrap_or(TR::words__address.into());

        let main_params = ConfirmBlobParams::new(title.unwrap_or(TString::empty()), message, None)
            .with_subtitle(subtitle)
            .with_menu_button()
            .with_footer(TR::instructions__swipe_up.into(), None)
            .with_chunkify(chunkify)
            .with_text_mono(text_mono)
            .with_swipe_up();

        let content_amount_params = amount.map(|amount| {
            ConfirmBlobParams::new(TR::words__amount.into(), amount, None)
                .with_subtitle(subtitle)
                .with_menu_button()
                .with_footer(TR::instructions__swipe_up.into(), None)
                .with_text_mono(text_mono)
                .with_swipe_up()
                .with_swipe_down()
        });

        let address_params = address.map(|address| {
            ConfirmBlobParams::new(address_title, address, None)
                .with_cancel_button()
                .with_chunkify(true)
                .with_text_mono(true)
                .with_swipe_right()
        });

        let mut fee_items_params =
            ShowInfoParams::new(TR::confirm_total__title_fee.into()).with_cancel_button();
        if fee_items.is_some() {
            for pair in IterBuf::new().try_iterate(fee_items.unwrap())? {
                let [label, value]: [TString; 2] = util::iter_into_array(pair)?;
                fee_items_params = unwrap!(fee_items_params.add(label, value));
            }
        }

        let summary_items_params: Option<ShowInfoParams> = if summary_items.is_some() {
            let mut summary =
                ShowInfoParams::new(summary_title.unwrap_or(TR::words__title_summary.into()))
                    .with_menu_button()
                    .with_footer(TR::instructions__swipe_up.into(), None)
                    .with_swipe_up()
                    .with_swipe_down();
            for pair in IterBuf::new().try_iterate(summary_items.unwrap())? {
                let [label, value]: [TString; 2] = util::iter_into_array(pair)?;
                summary = unwrap!(summary.add(label, value));
            }
            Some(summary)
        } else {
            None
        };

        let flow = flow::confirm_output::new_confirm_output(
            main_params,
            account,
            account_path,
            br_name,
            br_code,
            content_amount_params,
            address_params,
            address_title,
            summary_items_params,
            fee_items_params,
            summary_br_name,
            summary_br_code,
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
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(
            c"multiple_pages_texts not implemented",
        ))
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
        debug_assert!(
            description.is_some(),
            "Description is required for request_number"
        );
        debug_assert!(
            more_info_callback.is_some(),
            "More info callback is required for request_number"
        );
        let flow = flow::request_number::new_request_number(
            title,
            count,
            min_count,
            max_count,
            description.unwrap(),
            more_info_callback.unwrap(),
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
        let content = VerticalMenu::select_word(words);
        let layout =
            RootComponent::new(Frame::left_aligned(title, content).with_subtitle(description));
        Ok(layout)
    }

    fn select_word_count(recovery_type: RecoveryType) -> Result<impl LayoutMaybeTrace, Error> {
        let content = if matches!(recovery_type, RecoveryType::UnlockRepeatedBackup) {
            SelectWordCount::new_multishare()
        } else {
            SelectWordCount::new_all()
        };
        let layout = RootComponent::new(Frame::left_aligned(
            TR::recovery__num_of_words.into(),
            content,
        ));
        Ok(layout)
    }

    fn set_brightness(current_brightness: Option<u8>) -> Result<impl LayoutMaybeTrace, Error> {
        let flow = flow::set_brightness::new_set_brightness(current_brightness)?;
        Ok(flow)
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
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(
            c"show_address_details not implemented",
        ))
    }

    fn show_checklist(
        title: TString<'static>,
        _button: TString<'static>,
        active: usize,
        items: [TString<'static>; MAX_CHECKLIST_ITEMS],
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let mut paragraphs = ParagraphVecLong::new();
        for (i, item) in items.into_iter().enumerate() {
            let style = match i.cmp(&active) {
                Ordering::Less => &theme::TEXT_CHECKLIST_DONE,
                Ordering::Equal => &theme::TEXT_CHECKLIST_SELECTED,
                Ordering::Greater => &theme::TEXT_CHECKLIST_DEFAULT,
            };
            paragraphs.add(Paragraph::new(style, item));
        }

        let checklist_content = Checklist::from_paragraphs(
            theme::ICON_CHEVRON_RIGHT,
            theme::ICON_BULLET_CHECKMARK,
            active,
            paragraphs
                .into_paragraphs()
                .with_spacing(theme::CHECKLIST_SPACING),
        )
        .with_check_width(theme::CHECKLIST_CHECK_WIDTH)
        .with_numerals()
        .with_icon_done_color(theme::GREEN)
        .with_done_offset(theme::CHECKLIST_DONE_OFFSET);

        let layout = RootComponent::new(SwipeUpScreen::new(
            Frame::left_aligned(title, SwipeContent::new(checklist_content))
                .with_footer(TR::instructions__swipe_up.into(), None)
                .with_swipe(Direction::Up, SwipeSettings::default()),
        ));
        Ok(layout)
    }

    fn show_danger(
        title: TString<'static>,
        description: TString<'static>,
        value: TString<'static>,
        verb_cancel: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let flow = flow::show_danger::new_show_danger(title, description, value, verb_cancel)?;
        Ok(flow)
    }

    fn show_error(
        title: TString<'static>,
        _button: TString<'static>,
        description: TString<'static>,
        allow_cancel: bool,
        _time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error> {
        let content = Paragraphs::new(Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, description));
        let frame = if allow_cancel {
            Frame::left_aligned(title, SwipeContent::new(content))
                .with_cancel_button()
                .with_danger()
                .with_footer(TR::instructions__swipe_up.into(), None)
                .with_swipe(Direction::Up, SwipeSettings::default())
        } else {
            Frame::left_aligned(title, SwipeContent::new(content))
                .with_danger()
                .with_footer(TR::instructions__swipe_up.into(), None)
                .with_swipe(Direction::Up, SwipeSettings::default())
        };

        let obj = LayoutObj::new(SwipeUpScreen::new(frame))?;
        Ok(obj)
    }

    fn show_group_share_success(
        lines: [TString<'static>; MAX_GROUP_SHARE_LINES],
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let paragraphs = ParagraphVecShort::from_iter([
            Paragraph::new(&theme::TEXT_NORMAL_GREY_EXTRA_LIGHT, lines[0]).centered(),
            Paragraph::new(&theme::TEXT_DEMIBOLD, lines[1]).centered(),
            Paragraph::new(&theme::TEXT_NORMAL_GREY_EXTRA_LIGHT, lines[2]).centered(),
            Paragraph::new(&theme::TEXT_DEMIBOLD, lines[3]).centered(),
        ])
        .into_paragraphs()
        .with_placement(geometry::LinearPlacement::vertical().align_at_center());

        let layout = RootComponent::new(SwipeUpScreen::new(
            Frame::left_aligned("".into(), SwipeContent::new(paragraphs))
                .with_footer(TR::instructions__swipe_up.into(), None)
                .with_swipe(Direction::Up, SwipeSettings::default()),
        ));
        Ok(layout)
    }

    fn show_homescreen(
        label: TString<'static>,
        hold: bool,
        notification: Option<TString<'static>>,
        notification_level: u8,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let notification = notification.map(|w| (w, notification_level));
        let layout = RootComponent::new(Homescreen::new(label, notification, hold)?);
        Ok(layout)
    }

    fn show_info(
        title: TString<'static>,
        description: TString<'static>,
        _button: TString<'static>,
        _time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error> {
        let content = Paragraphs::new(Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, description));
        let obj = LayoutObj::new(SwipeUpScreen::new(
            Frame::left_aligned(title, SwipeContent::new(content))
                .with_footer(TR::instructions__swipe_up.into(), None)
                .with_swipe(Direction::Up, SwipeSettings::default()),
        ))?;
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
            paragraphs.add(Paragraph::new(&theme::TEXT_SUB_GREY, key).no_break());
            if chunkify {
                paragraphs.add(Paragraph::new(
                    theme::get_chunkified_text_style(value.len()),
                    value,
                ));
            } else {
                paragraphs.add(Paragraph::new(&theme::TEXT_MONO, value));
            }
        }

        let layout = RootComponent::new(SwipeUpScreen::new(
            Frame::left_aligned(title, SwipeContent::new(paragraphs.into_paragraphs()))
                .with_cancel_button(),
        ));
        Ok(layout)
    }

    fn show_lockscreen(
        label: TString<'static>,
        bootscreen: bool,
        coinjoin_authorized: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let layout = RootComponent::new(Lockscreen::new(label, bootscreen, coinjoin_authorized)?);
        Ok(layout)
    }

    fn show_mismatch(title: TString<'static>) -> Result<impl LayoutMaybeTrace, Error> {
        let description: TString = TR::addr_mismatch__contact_support_at.into();
        let url: TString = TR::addr_mismatch__support_url.into();
        let button: TString = TR::buttons__quit.into();

        let paragraphs = ParagraphVecShort::from_iter([
            Paragraph::new(&theme::TEXT_NORMAL, description).centered(),
            Paragraph::new(&theme::TEXT_DEMIBOLD, url).centered(),
        ])
        .into_paragraphs();

        let layout = RootComponent::new(SwipeUpScreen::new(
            Frame::left_aligned(title, SwipeContent::new(paragraphs))
                .with_cancel_button()
                .with_footer(TR::instructions__swipe_up.into(), Some(button))
                .with_swipe(Direction::Up, SwipeSettings::default()),
        ));

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

        let layout = RootComponent::new(Progress::new(title, indeterminate, description));
        Ok(layout)
    }

    fn show_progress_coinjoin(
        title: TString<'static>,
        indeterminate: bool,
        time_ms: u32,
        skip_first_paint: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        let progress = CoinJoinProgress::<Never>::new(title, indeterminate)?;
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
            c"use share_words_mercury instead",
        ))
    }

    fn show_share_words_mercury(
        words: heapless::Vec<TString<'static>, 33>,
        subtitle: Option<TString<'static>>,
        instructions: Obj,
        text_footer: Option<TString<'static>>,
        text_confirm: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let mut instructions_paragraphs = ParagraphVecShort::new();
        for item in IterBuf::new().try_iterate(instructions)? {
            let text: TString = item.try_into()?;
            instructions_paragraphs.add(Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, text));
        }

        let flow = flow::show_share_words::new_show_share_words(
            words,
            subtitle.unwrap_or(TString::empty()),
            instructions_paragraphs,
            text_footer,
            text_confirm,
        )?;
        Ok(flow)
    }

    fn show_remaining_shares(_pages_iterable: Obj) -> Result<impl LayoutMaybeTrace, Error> {
        // Mercury: remaining shares is a part of `continue_recovery` flow
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(
            c"show_remaining_shares not implemented",
        ))
    }

    fn show_simple(
        text: TString<'static>,
        _title: Option<TString<'static>>,
        _button: Option<TString<'static>>,
    ) -> Result<Gc<LayoutObj>, Error> {
        let obj = LayoutObj::new(Border::new(
            theme::borders(),
            Paragraphs::new(Paragraph::new(&theme::TEXT_DEMIBOLD, text)),
        ))?;
        Ok(obj)
    }

    fn show_success(
        title: TString<'static>,
        _button: TString<'static>,
        description: TString<'static>,
        _allow_cancel: bool,
        _time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error> {
        // description used in the Footer
        let description = if description.is_empty() {
            None
        } else {
            Some(description)
        };
        let content = StatusScreen::new_success(title);
        let layout = LayoutObj::new(SwipeUpScreen::new(
            Frame::left_aligned(
                TR::words__title_success.into(),
                SwipeContent::new(content).with_no_attach_anim(),
            )
            .with_footer(TR::instructions__swipe_up.into(), description)
            .with_result_icon(theme::ICON_BULLET_CHECKMARK, theme::GREEN_LIGHT)
            .with_swipe(Direction::Up, SwipeSettings::default()),
        ))?;
        Ok(layout)
    }

    fn show_wait_text(text: TString<'static>) -> Result<impl LayoutMaybeTrace, Error> {
        let layout = RootComponent::new(Connect::new(text, theme::FG, theme::BG));
        Ok(layout)
    }

    fn show_warning(
        title: TString<'static>,
        button: TString<'static>,
        value: TString<'static>,
        description: TString<'static>,
        _allow_cancel: bool,
        danger: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        let action = if button.is_empty() {
            None
        } else {
            Some(button)
        };
        let content = ParagraphVecShort::from_iter([
            Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, description),
            Paragraph::new(&theme::TEXT_MAIN_GREY_EXTRA_LIGHT, value),
        ])
        .into_paragraphs();

        let frame = Frame::left_aligned(title, SwipeContent::new(content))
            .with_footer(TR::instructions__swipe_up.into(), action)
            .with_swipe(Direction::Up, SwipeSettings::default());

        let frame_with_icon = if danger {
            frame.with_danger_icon()
        } else {
            frame.with_warning_low_icon()
        };

        let layout = LayoutObj::new(SwipeUpScreen::new(frame_with_icon))?;
        Ok(layout)
    }

    fn tutorial() -> Result<impl LayoutMaybeTrace, Error> {
        let flow = flow::show_tutorial::new_show_tutorial()?;
        Ok(flow)
    }
}
