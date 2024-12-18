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
            image::BlendedImage,
            text::{
                op::OpTextLayout,
                paragraphs::{
                    Checklist, Paragraph, ParagraphSource, ParagraphVecLong, ParagraphVecShort,
                    Paragraphs, VecExt,
                },
                TextStyle,
            },
            Border, ComponentExt, Empty, FormattedText, Jpeg, Label, Never, Timeout,
        },
        geometry,
        layout::{
            obj::{LayoutMaybeTrace, LayoutObj, RootComponent},
            util::{ConfirmBlob, PropsList, RecoveryType},
        },
        ui_firmware::{
            FirmwareUI, MAX_CHECKLIST_ITEMS, MAX_GROUP_SHARE_LINES, MAX_WORD_QUIZ_ITEMS,
        },
        ModelUI,
    },
};

use super::{
    component::{
        check_homescreen_format, AddressDetails, Bip39Input, Button, ButtonMsg, ButtonPage,
        ButtonStyleSheet, CancelConfirmMsg, CoinJoinProgress, Dialog, FidoConfirm, Frame,
        Homescreen, IconDialog, Lockscreen, MnemonicKeyboard, NumberInputDialog,
        PassphraseKeyboard, PinKeyboard, Progress, SelectWordCount, SetBrightnessDialog,
        ShareWords, SimplePage, Slip39Input,
    },
    theme, UIModelTT,
};

impl FirmwareUI for UIModelTT {
    fn confirm_action(
        title: TString<'static>,
        action: Option<TString<'static>>,
        description: Option<TString<'static>>,
        _subtitle: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        verb_cancel: Option<TString<'static>>,
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
                    .add(Paragraph::new(&theme::TEXT_DEMIBOLD, action))
                    .add(Paragraph::new(&theme::TEXT_NORMAL, description));
            } else {
                paragraphs
                    .add(Paragraph::new(&theme::TEXT_NORMAL, description))
                    .add(Paragraph::new(&theme::TEXT_DEMIBOLD, action));
            }
            paragraphs.into_paragraphs()
        };

        let mut page = if hold {
            ButtonPage::new(paragraphs, theme::BG).with_hold()?
        } else {
            ButtonPage::new(paragraphs, theme::BG).with_cancel_confirm(verb_cancel, verb)
        };
        if hold && hold_danger {
            page = page.with_confirm_style(theme::button_danger())
        }
        let layout = RootComponent::new(Frame::left_aligned(theme::label_title(), title, page));
        Ok(layout)
    }

    fn confirm_address(
        title: TString<'static>,
        address: Obj,
        address_label: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        info_button: bool,
        chunkify: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        let verb = verb.unwrap_or(TR::buttons__confirm.into());
        ConfirmBlobParams::new(title, address, None, Some(verb), None, false)
            .with_subtitle(address_label)
            .with_info_button(info_button)
            .with_chunkify(chunkify)
            .into_layout()
    }

    fn confirm_blob(
        title: TString<'static>,
        data: Obj,
        description: Option<TString<'static>>,
        text_mono: bool,
        extra: Option<TString<'static>>,
        _subtitle: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        verb_cancel: Option<TString<'static>>,
        _verb_info: Option<TString<'static>>,
        info: bool,
        hold: bool,
        chunkify: bool,
        _page_counter: bool,
        _prompt_screen: bool,
        _cancel: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        ConfirmBlobParams::new(title, data, description, verb, verb_cancel, hold)
            .with_text_mono(text_mono)
            .with_extra(extra)
            .with_chunkify(chunkify)
            .with_info_button(info)
            .into_layout()
    }

    fn confirm_blob_intro(
        _title: TString<'static>,
        _data: Obj,
        _subtitle: Option<TString<'static>>,
        _verb: Option<TString<'static>>,
        _verb_cancel: Option<TString<'static>>,
        _chunkify: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        Err::<Gc<LayoutObj>, Error>(Error::ValueError(c"confirm_blob_intro not implemented"))
    }

    fn confirm_homescreen(
        title: TString<'static>,
        mut image: BinaryData<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        if image.is_empty() {
            // Incoming data may be empty, meaning we should
            // display default homescreen image.
            image = theme::IMAGE_HOMESCREEN.into();
        }

        if !check_homescreen_format(image, false) {
            return Err(value_error!(c"Invalid image."));
        };

        let buttons = Button::cancel_confirm_text(None, Some(TR::buttons__change.into()));
        let layout = RootComponent::new(Frame::centered(
            theme::label_title(),
            title,
            Dialog::new(Jpeg::new(image, 1), buttons),
        ));
        Ok(layout)
    }

    fn confirm_coinjoin(
        max_rounds: TString<'static>,
        max_feerate: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let paragraphs = Paragraphs::new([
            Paragraph::new(&theme::TEXT_NORMAL, TR::coinjoin__max_rounds),
            Paragraph::new(&theme::TEXT_MONO, max_rounds),
            Paragraph::new(&theme::TEXT_NORMAL, TR::coinjoin__max_mining_fee),
            Paragraph::new(&theme::TEXT_MONO, max_feerate),
        ]);

        let layout = RootComponent::new(Frame::left_aligned(
            theme::label_title(),
            TR::coinjoin__title.into(),
            ButtonPage::new(paragraphs, theme::BG).with_hold()?,
        ));
        Ok(layout)
    }

    fn confirm_emphasized(
        title: TString<'static>,
        items: Obj,
        verb: Option<TString<'static>>,
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

        let layout = RootComponent::new(Frame::left_aligned(
            theme::label_title(),
            title,
            ButtonPage::new(FormattedText::new(ops).vertically_centered(), theme::BG)
                .with_cancel_confirm(None, verb),
        ));
        Ok(layout)
    }

    fn confirm_fido(
        title: TString<'static>,
        app_name: TString<'static>,
        icon: Option<TString<'static>>,
        accounts: Gc<List>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        // Cache the page count so that we can move `accounts` into the closure.
        let page_count = accounts.len();
        // Closure to lazy-load the information on given page index.
        // Done like this to allow arbitrarily many pages without
        // the need of any allocation here in Rust.
        let get_page = move |page_index| {
            let account = unwrap!(accounts.get(page_index));
            account.try_into().unwrap_or_else(|_| "".into())
        };

        let controls = Button::cancel_confirm(
            Button::with_icon(theme::ICON_CANCEL),
            Button::with_text(TR::buttons__confirm.into()).styled(theme::button_confirm()),
            true,
        );

        let fido_page = FidoConfirm::new(app_name, get_page, page_count, icon, controls);

        let layout = RootComponent::new(Frame::centered(theme::label_title(), title, fido_page));
        Ok(layout)
    }

    fn confirm_firmware_update(
        description: TString<'static>,
        fingerprint: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        use super::component::bl_confirm::{Confirm, ConfirmTitle};

        let title_str = TR::firmware_update__title.into();
        let title = Label::left_aligned(title_str, theme::TEXT_BOLD).vertically_centered();
        let msg = Label::left_aligned(description, theme::TEXT_NORMAL);

        let left = Button::with_text(TR::buttons__cancel.into()).styled(theme::button_default());
        let right = Button::with_text(TR::buttons__install.into()).styled(theme::button_confirm());

        let layout = RootComponent::new(
            Confirm::new(theme::BG, left, right, ConfirmTitle::Text(title), msg).with_info(
                TR::firmware_update__title_fingerprint.into(),
                fingerprint,
                theme::button_moreinfo(),
            ),
        );
        Ok(layout)
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

        let paragraphs = Paragraphs::new([
            Paragraph::new(&theme::TEXT_NORMAL, description),
            Paragraph::new(&theme::TEXT_MONO, change),
            Paragraph::new(&theme::TEXT_NORMAL, total_label),
            Paragraph::new(&theme::TEXT_MONO, total_fee_new),
        ]);

        let layout = RootComponent::new(
            Frame::left_aligned(
                theme::label_title(),
                title,
                ButtonPage::new(paragraphs, theme::BG)
                    .with_hold()?
                    .with_swipe_left(),
            )
            .with_info_button(),
        );
        Ok(layout)
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

        let paragraphs = Paragraphs::new([
            Paragraph::new(&theme::TEXT_NORMAL, description),
            Paragraph::new(&theme::TEXT_MONO, amount_change),
            Paragraph::new(&theme::TEXT_NORMAL, TR::modify_amount__new_amount),
            Paragraph::new(&theme::TEXT_MONO, amount_new),
        ]);

        let layout = RootComponent::new(Frame::left_aligned(
            theme::label_title(),
            TR::modify_amount__title.into(),
            ButtonPage::new(paragraphs, theme::BG)
                .with_cancel_confirm(Some("^".into()), Some(TR::buttons__continue.into())),
        ));
        Ok(layout)
    }

    fn confirm_more(
        title: TString<'static>,
        button: TString<'static>,
        button_style_confirm: bool,
        items: Obj,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let mut paragraphs = ParagraphVecLong::new();

        for para in IterBuf::new().try_iterate(items)? {
            let [font, text]: [Obj; 2] = util::iter_into_array(para)?;
            let style: &TextStyle = theme::textstyle_number(font.try_into()?);
            let text: TString = text.try_into()?;
            paragraphs.add(Paragraph::new(style, text));
        }

        let layout = RootComponent::new(Frame::left_aligned(
            theme::label_title(),
            title,
            ButtonPage::new(paragraphs.into_paragraphs(), theme::BG)
                .with_cancel_confirm(None, Some(button))
                .with_confirm_style(if button_style_confirm {
                    theme::button_confirm()
                } else {
                    theme::button_default()
                })
                .with_back_button(),
        ));
        Ok(layout)
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
        let page = if hold {
            ButtonPage::new(paragraphs.into_paragraphs(), theme::BG).with_hold()?
        } else {
            ButtonPage::new(paragraphs.into_paragraphs(), theme::BG)
                .with_cancel_confirm(None, Some(TR::buttons__confirm.into()))
        };
        let layout = RootComponent::new(Frame::left_aligned(theme::label_title(), title, page));
        Ok(layout)
    }

    fn confirm_reset_device(recovery: bool) -> Result<impl LayoutMaybeTrace, Error> {
        let (title, button) = if recovery {
            (
                TR::recovery__title_recover.into(),
                TR::reset__button_recover.into(),
            )
        } else {
            (
                TR::reset__title_create_wallet.into(),
                TR::reset__button_create.into(),
            )
        };
        let par_array: [Paragraph<'static>; 3] = [
            Paragraph::new(&theme::TEXT_NORMAL, TR::reset__by_continuing).with_bottom_padding(17), /* simulating a carriage return */
            Paragraph::new(&theme::TEXT_NORMAL, TR::reset__more_info_at),
            Paragraph::new(&theme::TEXT_DEMIBOLD, TR::reset__tos_link),
        ];
        let paragraphs = Paragraphs::new(par_array);
        let buttons = Button::cancel_confirm(
            Button::with_icon(theme::ICON_CANCEL),
            Button::with_text(button).styled(theme::button_confirm()),
            true,
        );
        let layout = RootComponent::new(Frame::left_aligned(
            theme::label_title(),
            title,
            Dialog::new(paragraphs, buttons),
        ));
        Ok(layout)
    }

    fn confirm_summary(
        amount: TString<'static>,
        amount_label: TString<'static>,
        fee: TString<'static>,
        fee_label: TString<'static>,
        title: Option<TString<'static>>,
        account_items: Option<Obj>,
        extra_items: Option<Obj>,
        _extra_title: Option<TString<'static>>,
        verb_cancel: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let info_button: bool = account_items.is_some() || extra_items.is_some();
        let paragraphs = ParagraphVecShort::from_iter([
            Paragraph::new(&theme::TEXT_NORMAL, amount_label).no_break(),
            Paragraph::new(&theme::TEXT_MONO, amount),
            Paragraph::new(&theme::TEXT_NORMAL, fee_label).no_break(),
            Paragraph::new(&theme::TEXT_MONO, fee),
        ]);

        let mut page = ButtonPage::new(paragraphs.into_paragraphs(), theme::BG)
            .with_hold()?
            .with_cancel_button(verb_cancel);
        if info_button {
            page = page.with_swipe_left();
        }
        let mut frame = Frame::left_aligned(
            theme::label_title(),
            title.unwrap_or(TString::empty()),
            page,
        );
        if info_button {
            frame = frame.with_info_button();
        }
        let layout = RootComponent::new(frame);
        Ok(layout)
    }

    fn confirm_value(
        title: TString<'static>,
        value: Obj,
        description: Option<TString<'static>>,
        subtitle: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        _verb_info: Option<TString<'static>>,
        verb_cancel: Option<TString<'static>>,
        info_button: bool,
        hold: bool,
        chunkify: bool,
        text_mono: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        ConfirmBlobParams::new(title, value, description, verb, verb_cancel, hold)
            .with_subtitle(subtitle)
            .with_info_button(info_button)
            .with_chunkify(chunkify)
            .with_text_mono(text_mono)
            .into_layout()
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

        let buttons = Button::cancel_info_confirm(button, info_button);

        let layout = RootComponent::new(Frame::left_aligned(
            theme::label_title(),
            title,
            Dialog::new(paragraphs.into_paragraphs(), buttons),
        ));
        Ok(layout)
    }

    fn check_homescreen_format(image: BinaryData, _accept_toif: bool) -> bool {
        super::component::check_homescreen_format(image, false)
    }

    fn continue_recovery_homepage(
        text: TString<'static>,
        subtext: Option<TString<'static>>,
        button: Option<TString<'static>>,
        recovery_type: RecoveryType,
        _show_instructions: bool,
        remaining_shares: Option<Obj>,
    ) -> Result<Gc<LayoutObj>, Error> {
        let paragraphs = Paragraphs::new([
            Paragraph::new(&theme::TEXT_DEMIBOLD, text),
            Paragraph::new(&theme::TEXT_NORMAL, subtext.unwrap_or(TString::empty())),
        ])
        .with_spacing(theme::RECOVERY_SPACING);

        let notification = match recovery_type {
            RecoveryType::DryRun => TR::recovery__title_dry_run.into(),
            RecoveryType::UnlockRepeatedBackup => TR::recovery__title_dry_run.into(),
            _ => TR::recovery__title.into(),
        };

        // Model T shows remaining shares info in a separate layout
        let show_info_button = remaining_shares.is_some();
        if show_info_button {
            LayoutObj::new(Frame::left_aligned(
                theme::label_title(),
                notification,
                Dialog::new(
                    paragraphs,
                    Button::cancel_info_confirm(
                        TR::buttons__continue.into(),
                        TR::buttons__more_info.into(),
                    ),
                ),
            ))
        } else {
            LayoutObj::new(Frame::left_aligned(
                theme::label_title(),
                notification,
                Dialog::new(paragraphs, Button::cancel_confirm_text(None, button)),
            ))
        }
    }

    fn flow_confirm_output(
        _title: Option<TString<'static>>,
        _subtitle: Option<TString<'static>>,
        _message: Obj,
        _amount: Option<Obj>,
        _chunkify: bool,
        _text_mono: bool,
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
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(
            c"flow_confirm_output not supported",
        ))
    }

    fn flow_confirm_set_new_pin(
        _title: TString<'static>,
        _description: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(
            c"flow_confirm_set_new_pin not supported",
        ))
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
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(
            c"flow_get_address not supported",
        ))
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
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(
            c"prompt_backup not implemented",
        ))
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
        _description: Option<TString<'static>>,
        more_info_callback: Option<impl Fn(u32) -> TString<'static> + 'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        debug_assert!(more_info_callback.is_some());
        let layout = RootComponent::new(Frame::left_aligned(
            theme::label_title(),
            title,
            NumberInputDialog::new(min_count, max_count, count, more_info_callback.unwrap())?,
        ));
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
        let layout = RootComponent::new(PassphraseKeyboard::new());
        Ok(layout)
    }

    fn select_word(
        title: TString<'static>,
        description: TString<'static>,
        words: [TString<'static>; MAX_WORD_QUIZ_ITEMS],
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let paragraphs = Paragraphs::new([Paragraph::new(&theme::TEXT_DEMIBOLD, description)]);
        let layout = RootComponent::new(Frame::left_aligned(
            theme::label_title(),
            title,
            Dialog::new(paragraphs, Button::select_word(words)),
        ));
        Ok(layout)
    }

    fn select_word_count(recovery_type: RecoveryType) -> Result<impl LayoutMaybeTrace, Error> {
        let title: TString = match recovery_type {
            RecoveryType::DryRun => TR::recovery__title_dry_run.into(),
            RecoveryType::UnlockRepeatedBackup => TR::recovery__title_dry_run.into(),
            _ => TR::recovery__title.into(),
        };

        let paragraphs = Paragraphs::new(Paragraph::new(
            &theme::TEXT_DEMIBOLD,
            TR::recovery__num_of_words,
        ));

        let content = if matches!(recovery_type, RecoveryType::UnlockRepeatedBackup) {
            SelectWordCount::new_multishare()
        } else {
            SelectWordCount::new_all()
        };

        let layout = RootComponent::new(Frame::left_aligned(
            theme::label_title(),
            title,
            Dialog::new(paragraphs, content),
        ));
        Ok(layout)
    }

    fn set_brightness(current_brightness: Option<u8>) -> Result<impl LayoutMaybeTrace, Error> {
        let layout = RootComponent::new(Frame::centered(
            theme::label_title(),
            TR::brightness__title.into(),
            SetBrightnessDialog::new(
                current_brightness.unwrap_or(theme::backlight::get_backlight_normal()),
            ),
        ));

        Ok(layout)
    }

    fn show_address_details(
        qr_title: TString<'static>,
        address: TString<'static>,
        case_sensitive: bool,
        details_title: TString<'static>,
        account: Option<TString<'static>>,
        path: Option<TString<'static>>,
        xpubs: Obj,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let mut ad = AddressDetails::new(
            qr_title,
            address,
            case_sensitive,
            details_title,
            account,
            path,
        )?;

        for i in IterBuf::new().try_iterate(xpubs)? {
            let [xtitle, text]: [TString; 2] = util::iter_into_array(i)?;
            ad.add_xpub(xtitle, text)?;
        }

        let layout =
            RootComponent::new(SimplePage::horizontal(ad, theme::BG).with_swipe_right_to_go_back());
        Ok(layout)
    }

    fn show_checklist(
        title: TString<'static>,
        button: TString<'static>,
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

        let layout = RootComponent::new(Frame::left_aligned(
            theme::label_title(),
            title,
            Dialog::new(
                Checklist::from_paragraphs(
                    theme::ICON_LIST_CURRENT,
                    theme::ICON_LIST_CHECK,
                    active,
                    paragraphs
                        .into_paragraphs()
                        .with_spacing(theme::CHECKLIST_SPACING),
                )
                .with_check_width(theme::CHECKLIST_CHECK_WIDTH)
                .with_current_offset(theme::CHECKLIST_CURRENT_OFFSET)
                .with_done_offset(theme::CHECKLIST_DONE_OFFSET),
                theme::button_bar(Button::with_text(button).map(|msg| {
                    (matches!(msg, ButtonMsg::Clicked)).then(|| CancelConfirmMsg::Confirmed)
                })),
            ),
        ));
        Ok(layout)
    }

    fn show_danger(
        _title: TString<'static>,
        _description: TString<'static>,
        _value: TString<'static>,
        _verb_cancel: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"show_danger not supported"))
    }

    fn show_error(
        title: TString<'static>,
        button: TString<'static>,
        description: TString<'static>,
        allow_cancel: bool,
        time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error> {
        let icon = BlendedImage::new(
            theme::IMAGE_BG_CIRCLE,
            theme::IMAGE_FG_ERROR,
            theme::ERROR_COLOR,
            theme::FG,
            theme::BG,
        );
        new_show_modal(
            title,
            TString::empty(),
            description,
            button,
            allow_cancel,
            time_ms,
            icon,
            theme::button_default(),
        )
    }

    fn show_group_share_success(
        lines: [TString<'static>; MAX_GROUP_SHARE_LINES],
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let layout = RootComponent::new(IconDialog::new_shares(
            lines,
            theme::button_bar(Button::with_text(TR::buttons__continue.into()).map(|msg| {
                (matches!(msg, ButtonMsg::Clicked)).then(|| CancelConfirmMsg::Confirmed)
            })),
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
        let layout = RootComponent::new(Homescreen::new(label, notification, hold));
        Ok(layout)
    }

    fn show_info(
        title: TString<'static>,
        description: TString<'static>,
        button: TString<'static>,
        time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error> {
        assert!(
            !button.is_empty() || time_ms > 0,
            "either button or timeout must be set"
        );

        let icon = BlendedImage::new(
            theme::IMAGE_BG_CIRCLE,
            theme::IMAGE_FG_INFO,
            theme::INFO_COLOR,
            theme::FG,
            theme::BG,
        );
        new_show_modal(
            title,
            TString::empty(),
            description,
            button,
            false,
            time_ms,
            icon,
            theme::button_info(),
        )
    }

    fn show_info_with_cancel(
        title: TString<'static>,
        items: Obj,
        horizontal: bool,
        chunkify: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let mut paragraphs = ParagraphVecShort::new();

        for para in IterBuf::new().try_iterate(items)? {
            let [key, value]: [Obj; 2] = util::iter_into_array(para)?;
            let key: TString = key.try_into()?;
            let value: TString = value.try_into()?;
            paragraphs.add(Paragraph::new(&theme::TEXT_NORMAL, key).no_break());
            if chunkify {
                paragraphs.add(Paragraph::new(
                    theme::get_chunkified_text_style(value.len()),
                    value,
                ));
            } else {
                paragraphs.add(Paragraph::new(&theme::TEXT_MONO, value));
            }
        }

        let axis = match horizontal {
            true => geometry::Axis::Horizontal,
            _ => geometry::Axis::Vertical,
        };

        let layout = RootComponent::new(
            Frame::left_aligned(
                theme::label_title(),
                title,
                SimplePage::new(paragraphs.into_paragraphs(), axis, theme::BG)
                    .with_swipe_right_to_go_back(),
            )
            .with_cancel_button(),
        );
        Ok(layout)
    }

    fn show_lockscreen(
        label: TString<'static>,
        bootscreen: bool,
        coinjoin_authorized: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let layout = RootComponent::new(Lockscreen::new(label, bootscreen, coinjoin_authorized));
        Ok(layout)
    }

    fn show_mismatch(title: TString<'static>) -> Result<impl LayoutMaybeTrace, Error> {
        let description: TString = TR::addr_mismatch__contact_support_at.into();
        let url: TString = TR::addr_mismatch__support_url.into();
        let button: TString = TR::buttons__quit.into();

        let icon = BlendedImage::new(
            theme::IMAGE_BG_OCTAGON,
            theme::IMAGE_FG_WARN,
            theme::WARN_COLOR,
            theme::FG,
            theme::BG,
        );
        let layout = RootComponent::new(
            IconDialog::new(
                icon,
                title,
                Button::cancel_confirm(
                    Button::with_icon(theme::ICON_BACK),
                    Button::with_text(button).styled(theme::button_reset()),
                    true,
                ),
            )
            .with_paragraph(
                Paragraph::new(&theme::TEXT_NORMAL, description)
                    .centered()
                    .with_bottom_padding(
                        theme::TEXT_NORMAL.text_font.text_height()
                            - theme::TEXT_DEMIBOLD.text_font.text_height(),
                    ),
            )
            .with_text(&theme::TEXT_DEMIBOLD, url),
        );

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
        words: heapless::Vec<TString<'static>, 33>,
        title: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let layout = RootComponent::new(Frame::left_aligned(
            theme::label_title(),
            title.unwrap_or(TString::empty()),
            ButtonPage::new(ShareWords::new(words), theme::BG)
                .with_hold()?
                .without_cancel(),
        ));
        Ok(layout)
    }

    fn show_share_words_mercury(
        _words: heapless::Vec<TString<'static>, 33>,
        _subtitle: Option<TString<'static>>,
        _instructions: Obj,
        _text_footer: Option<TString<'static>>,
        _text_confirm: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"use show_share_words"))
    }

    fn show_remaining_shares(pages_iterable: Obj) -> Result<impl LayoutMaybeTrace, Error> {
        let mut paragraphs = ParagraphVecLong::new();
        for page in crate::micropython::iter::IterBuf::new().try_iterate(pages_iterable)? {
            let [title, description]: [TString; 2] =
                crate::micropython::util::iter_into_array(page)?;
            paragraphs
                .add(Paragraph::new(&theme::TEXT_DEMIBOLD, title))
                .add(Paragraph::new(&theme::TEXT_NORMAL, description).break_after());
        }

        let layout = RootComponent::new(Frame::left_aligned(
            theme::label_title(),
            TR::recovery__title_remaining_shares.into(),
            ButtonPage::new(paragraphs.into_paragraphs(), theme::BG)
                .with_cancel_confirm(None, Some(TR::buttons__continue.into()))
                .with_confirm_style(theme::button_default())
                .without_cancel(),
        ));
        Ok(layout)
    }

    fn show_simple(
        text: TString<'static>,
        title: Option<TString<'static>>,
        button: Option<TString<'static>>,
    ) -> Result<Gc<LayoutObj>, Error> {
        let button = button.unwrap_or(TString::empty());
        if let Some(t) = title {
            LayoutObj::new(Frame::left_aligned(
                theme::label_title(),
                t,
                Dialog::new(
                    Paragraphs::new([Paragraph::new(&theme::TEXT_NORMAL, text)]),
                    theme::button_bar(Button::with_text(button).map(|msg| {
                        (matches!(msg, ButtonMsg::Clicked)).then(|| CancelConfirmMsg::Confirmed)
                    })),
                ),
            ))
        } else if !button.is_empty() {
            LayoutObj::new(Border::new(
                theme::borders(),
                Dialog::new(
                    Paragraphs::new([Paragraph::new(&theme::TEXT_NORMAL, text)]),
                    theme::button_bar(Button::with_text(button).map(|msg| {
                        (matches!(msg, ButtonMsg::Clicked)).then(|| CancelConfirmMsg::Confirmed)
                    })),
                ),
            ))
        } else {
            LayoutObj::new(Border::new(
                theme::borders(),
                Dialog::new(
                    Paragraphs::new([Paragraph::new(&theme::TEXT_DEMIBOLD, text).centered()]),
                    Empty,
                ),
            ))
        }
    }

    fn show_success(
        title: TString<'static>,
        button: TString<'static>,
        description: TString<'static>,
        allow_cancel: bool,
        time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error> {
        let icon = BlendedImage::new(
            theme::IMAGE_BG_CIRCLE,
            theme::IMAGE_FG_SUCCESS,
            theme::SUCCESS_COLOR,
            theme::FG,
            theme::BG,
        );
        new_show_modal(
            title,
            TString::empty(),
            description,
            button,
            allow_cancel,
            time_ms,
            icon,
            theme::button_confirm(),
        )
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
        allow_cancel: bool,
        _danger: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        let icon = BlendedImage::new(
            theme::IMAGE_BG_OCTAGON,
            theme::IMAGE_FG_WARN,
            theme::WARN_COLOR,
            theme::FG,
            theme::BG,
        );
        new_show_modal(
            title,
            value,
            description,
            button,
            allow_cancel,
            0,
            icon,
            theme::button_reset(),
        )
    }

    fn tutorial() -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(c"tutorial not supported"))
    }
}

#[allow(clippy::too_many_arguments)]
fn new_show_modal(
    title: TString<'static>,
    value: TString<'static>,
    description: TString<'static>,
    button: TString<'static>,
    allow_cancel: bool,
    time_ms: u32,
    icon: BlendedImage,
    button_style: ButtonStyleSheet,
) -> Result<Gc<LayoutObj>, Error> {
    let no_buttons = button.is_empty();
    let obj = if no_buttons && time_ms == 0 {
        // No buttons and no timer, used when we only want to draw the dialog once and
        // then throw away the layout object.
        LayoutObj::new(
            IconDialog::new(icon, title, Empty)
                .with_value(value)
                .with_description(description),
        )?
    } else if no_buttons && time_ms > 0 {
        // Timeout, no buttons.
        LayoutObj::new(
            IconDialog::new(
                icon,
                title,
                Timeout::new(time_ms).map(|_| Some(CancelConfirmMsg::Confirmed)),
            )
            .with_value(value)
            .with_description(description),
        )?
    } else if allow_cancel {
        // Two buttons.
        LayoutObj::new(
            IconDialog::new(
                icon,
                title,
                Button::cancel_confirm(
                    Button::with_icon(theme::ICON_CANCEL),
                    Button::with_text(button).styled(button_style),
                    false,
                ),
            )
            .with_value(value)
            .with_description(description),
        )?
    } else {
        // Single button.
        LayoutObj::new(
            IconDialog::new(
                icon,
                title,
                theme::button_bar(Button::with_text(button).styled(button_style).map(|msg| {
                    (matches!(msg, ButtonMsg::Clicked)).then(|| CancelConfirmMsg::Confirmed)
                })),
            )
            .with_value(value)
            .with_description(description),
        )?
    };

    Ok(obj)
}

// TODO: move to some util.rs?
struct ConfirmBlobParams {
    title: TString<'static>,
    subtitle: Option<TString<'static>>,
    data: Obj,
    description: Option<TString<'static>>,
    extra: Option<TString<'static>>,
    verb: Option<TString<'static>>,
    verb_cancel: Option<TString<'static>>,
    info_button: bool,
    hold: bool,
    chunkify: bool,
    text_mono: bool,
}

impl ConfirmBlobParams {
    fn new(
        title: TString<'static>,
        data: Obj,
        description: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        verb_cancel: Option<TString<'static>>,
        hold: bool,
    ) -> Self {
        Self {
            title,
            subtitle: None,
            data,
            description,
            extra: None,
            verb,
            verb_cancel,
            info_button: false,
            hold,
            chunkify: false,
            text_mono: true,
        }
    }

    fn with_extra(mut self, extra: Option<TString<'static>>) -> Self {
        self.extra = extra;
        self
    }

    fn with_subtitle(mut self, subtitle: Option<TString<'static>>) -> Self {
        self.subtitle = subtitle;
        self
    }

    fn with_info_button(mut self, info_button: bool) -> Self {
        self.info_button = info_button;
        self
    }

    fn with_chunkify(mut self, chunkify: bool) -> Self {
        self.chunkify = chunkify;
        self
    }

    fn with_text_mono(mut self, text_mono: bool) -> Self {
        self.text_mono = text_mono;
        self
    }

    fn into_layout(self) -> Result<Gc<LayoutObj>, Error> {
        let paragraphs = ConfirmBlob {
            description: self.description.unwrap_or("".into()),
            extra: self.extra.unwrap_or("".into()),
            data: self.data.try_into()?,
            description_font: &theme::TEXT_NORMAL,
            extra_font: &theme::TEXT_DEMIBOLD,
            data_font: if self.chunkify {
                let data: TString = self.data.try_into()?;
                theme::get_chunkified_text_style(data.len())
            } else if self.text_mono {
                &theme::TEXT_MONO
            } else {
                &theme::TEXT_NORMAL
            },
        }
        .into_paragraphs();

        let mut page = ButtonPage::new(paragraphs, theme::BG);
        if let Some(verb) = self.verb {
            page = page.with_cancel_confirm(self.verb_cancel, Some(verb))
        }
        if self.hold {
            page = page.with_hold()?
        }
        let mut frame = Frame::left_aligned(theme::label_title(), self.title, page);
        if let Some(subtitle) = self.subtitle {
            frame = frame.with_subtitle(theme::label_subtitle(), subtitle);
        }

        if self.info_button {
            frame = frame.with_info_button();
        }
        LayoutObj::new(frame)
    }
}

#[cfg(test)]
mod tests {
    use serde_json;

    use crate::{
        trace::tests::trace,
        ui::{
            component::{text::op::OpTextLayout, Component},
            geometry::Rect,
            model_tt::constant,
        },
    };

    use super::*;

    const SCREEN: Rect = constant::screen().inset(theme::borders());

    #[test]
    fn trace_example_layout() {
        let buttons = Button::cancel_confirm(
            Button::with_text("Left".into()),
            Button::with_text("Right".into()),
            false,
        );

        let ops = OpTextLayout::new(theme::TEXT_NORMAL)
            .text_normal("Testing text layout, with some text, and some more text. And ")
            .text_bold_upper("parameters!");
        let formatted = FormattedText::new(ops);
        let mut layout = Dialog::new(formatted, buttons);
        layout.place(SCREEN);

        let expected = serde_json::json!({
            "component": "Dialog",
            "content": {
                "component": "FormattedText",
                "text": ["Testing text layout, with", "\n", "some text, and some", "\n",
                "more text. And ", "parame", "-", "\n", "ters!"],
                "fits": true,
            },
            "controls": {
                "component": "FixedHeightBar",
                "inner": {
                    "component": "Split",
                    "first": {
                        "component": "Button",
                        "text": "Left",
                    },
                    "second": {
                        "component": "Button",
                        "text": "Right",
                    },
                },
            },
        });

        assert_eq!(trace(&layout), expected);
    }
}
