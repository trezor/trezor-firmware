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
        geometry::{self, Direction, Offset},
        layout::{
            obj::{LayoutMaybeTrace, LayoutObj, RootComponent},
            util::{PropsList, RecoveryType},
        },
        ui_firmware::{
            FirmwareUI, ERROR_NOT_IMPLEMENTED, MAX_CHECKLIST_ITEMS, MAX_GROUP_SHARE_LINES,
            MAX_WORD_QUIZ_ITEMS,
        },
        ModelUI,
    },
};

use super::{
    component::{
        check_homescreen_format, Bip39Input, CoinJoinProgress, Frame, Homescreen, Lockscreen,
        MnemonicKeyboard, PinKeyboard, Progress, SelectWordCount, SelectWordCountLayout,
        Slip39Input, StatusScreen, SwipeContent, SwipeUpScreen, VerticalMenu,
    },
    flow::{self},
    fonts, theme, UIDelizia,
};

impl FirmwareUI for UIDelizia {
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
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
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
        Err::<Gc<LayoutObj>, Error>(ERROR_NOT_IMPLEMENTED)
    }

    fn confirm_value(
        title: TString<'static>,
        value: Obj,
        description: Option<TString<'static>>,
        is_data: bool,
        extra: Option<TString<'static>>,
        subtitle: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        verb_cancel: Option<TString<'static>>,
        info: bool,
        hold: bool,
        chunkify: bool,
        page_counter: bool,
        prompt_screen: bool,
        cancel: bool,
        _warning_footer: Option<TString<'static>>,
    ) -> Result<Gc<LayoutObj>, Error> {
        Err::<Gc<LayoutObj>, Error>(ERROR_NOT_IMPLEMENTED)
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
        Err::<Gc<LayoutObj>, Error>(ERROR_NOT_IMPLEMENTED)
    }

    fn confirm_homescreen(
        title: TString<'static>,
        image: BinaryData<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
    }

    fn confirm_coinjoin(
        max_rounds: TString<'static>,
        max_feerate: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
    }

    fn confirm_emphasized(
        title: TString<'static>,
        items: Obj,
        _verb: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
    }

    fn confirm_fido(
        title: TString<'static>,
        app_name: TString<'static>,
        icon: Option<TString<'static>>,
        accounts: Gc<List>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
    }

    fn confirm_firmware_update(
        description: TString<'static>,
        fingerprint: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
    }

    fn confirm_modify_fee(
        title: TString<'static>,
        sign: i32,
        user_fee_change: TString<'static>,
        total_fee_new: TString<'static>,
        _fee_rate_amount: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
    }

    fn confirm_modify_output(
        sign: i32,
        amount_change: TString<'static>,
        amount_new: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
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
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
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
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
    }

    fn confirm_properties(
        title: TString<'static>,
        subtitle: Option<TString<'static>>,
        items: Obj,
        hold: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
    }

    fn confirm_with_info(
        title: TString<'static>,
        items: Obj,
        verb: TString<'static>,
        verb_info: TString<'static>,
        _verb_cancel: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
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
        Err::<Gc<LayoutObj>, Error>(ERROR_NOT_IMPLEMENTED)
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
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
    }

    fn multiple_pages_texts(
        _title: TString<'static>,
        _verb: TString<'static>,
        _items: Gc<List>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
    }

    fn prompt_backup() -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
    }

    fn request_bip39(
        prompt: TString<'static>,
        prefill_word: TString<'static>,
        can_go_back: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
    }

    fn request_slip39(
        prompt: TString<'static>,
        prefill_word: TString<'static>,
        can_go_back: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
    }

    fn request_number(
        title: TString<'static>,
        count: u32,
        min_count: u32,
        max_count: u32,
        description: Option<TString<'static>>,
        more_info_callback: Option<impl Fn(u32) -> TString<'static> + 'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
    }

    fn request_duration(
        _title: TString<'static>,
        _duration_ms: u32,
        _min_ms: u32,
        _max_ms: u32,
        _description: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
    }

    fn request_pin(
        prompt: TString<'static>,
        subprompt: TString<'static>,
        allow_cancel: bool,
        warning: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
    }

    fn request_passphrase(
        _prompt: TString<'static>,
        _max_len: u32,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
    }

    fn select_word(
        title: TString<'static>,
        description: TString<'static>,
        words: [TString<'static>; MAX_WORD_QUIZ_ITEMS],
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
    }

    fn select_word_count(recovery_type: RecoveryType) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
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
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
    }

    fn show_checklist(
        title: TString<'static>,
        _button: TString<'static>,
        active: usize,
        items: [TString<'static>; MAX_CHECKLIST_ITEMS],
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
    }

    fn show_danger(
        title: TString<'static>,
        description: TString<'static>,
        value: TString<'static>,
        _menu_title: Option<TString<'static>>,
        verb_cancel: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
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
                .with_swipeup_footer(None)
        } else {
            Frame::left_aligned(title, SwipeContent::new(content))
                .with_danger()
                .with_swipeup_footer(None)
        };

        let obj = LayoutObj::new(SwipeUpScreen::new(frame))?;
        Ok(obj)
    }

    fn show_group_share_success(
        lines: [TString<'static>; MAX_GROUP_SHARE_LINES],
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
    }

    fn show_homescreen(
        label: TString<'static>,
        notification: Option<TString<'static>>,
        notification_level: u8,
        lockable: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let notification = notification.map(|w| (w, notification_level));
        let layout = RootComponent::new(Homescreen::new(label, notification, lockable)?);
        Ok(layout)
    }

    fn show_device_menu(
        _failed_backup: bool,
        _firmware_version: TString<'static>,
        _device_name: TString<'static>,
        _paired_devices: heapless::Vec<TString<'static>, 1>,
        _auto_lock_delay: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(
            c"show_device_menu not supported",
        ))
    }

    fn show_pairing_device_name(
        _device_name: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(
            c"show_pairing_device_name not supported",
        ))
    }

    fn show_pairing_code(
        _title: TString<'static>,
        _description: TString<'static>,
        _code: TString<'static>,
        _button: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::ValueError(
            c"show_pairing_code not supported",
        ))
    }

    fn show_info(
        title: TString<'static>,
        description: TString<'static>,
        _button: TString<'static>,
        _time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error> {
        unimplemented!()
    }

    fn show_info_with_cancel(
        title: TString<'static>,
        items: Obj,
        _horizontal: bool,
        chunkify: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::RuntimeError(c"Not implemented"))
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
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::RuntimeError(c"Not implemented"))
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
            c"use show_share_words_extended instead",
        ))
    }

    fn show_share_words_extended(
        words: heapless::Vec<TString<'static>, 33>,
        subtitle: Option<TString<'static>>,
        instructions: Obj,
        _instructions_verb: Option<TString<'static>>,
        text_footer: Option<TString<'static>>,
        text_confirm: TString<'static>,
        text_check: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::RuntimeError(c"Not implemented"))
    }

    fn show_remaining_shares(_pages_iterable: Obj) -> Result<impl LayoutMaybeTrace, Error> {
        // Delizia: remaining shares is a part of `continue_recovery` flow
        Err::<RootComponent<Empty, ModelUI>, Error>(ERROR_NOT_IMPLEMENTED)
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
        button: TString<'static>,
        description: TString<'static>,
        _allow_cancel: bool,
        time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error> {
        let instruction = if button.is_empty() {
            TR::instructions__tap_to_continue.into()
        } else {
            button
        };
        // description used in the Footer
        let description = if description.is_empty() {
            None
        } else {
            Some(description)
        };
        let content = if time_ms > 0 {
            StatusScreen::new_success_timeout(title, time_ms)
        } else {
            StatusScreen::new_success(title)
        };
        let layout = LayoutObj::new(SwipeUpScreen::new(
            Frame::left_aligned(
                TR::words__title_success.into(),
                SwipeContent::new(content).with_no_attach_anim(),
            )
            .with_footer(instruction, description)
            .with_swipe(Direction::Up, SwipeSettings::default())
            .with_result_icon(theme::ICON_BULLET_CHECKMARK, theme::GREEN_LIGHT),
        ))?;
        Ok(layout)
    }

    fn show_wait_text(text: TString<'static>) -> Result<impl LayoutMaybeTrace, Error> {
        let layout = RootComponent::new(Connect::new(
            text,
            fonts::FONT_DEMIBOLD,
            theme::FG,
            theme::BG,
        ));
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

        let frame = Frame::left_aligned(title, SwipeContent::new(content));
        let frame = if danger {
            frame.with_danger_icon().with_tap_footer(action)
        } else {
            frame.with_warning_low_icon().with_swipeup_footer(action)
        };

        let layout = LayoutObj::new(SwipeUpScreen::new(frame))?;
        Ok(layout)
    }

    fn tutorial() -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::RuntimeError(c"Not implemented"))
    }

    fn flow_confirm_set_new_pin(
        title: TString<'static>,
        description: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::RuntimeError(c"Not implemented"))
    }

    fn flow_get_address(
        address: Obj, // TODO: replace Obj
        title: TString<'static>,
        description: Option<TString<'static>>,
        extra: Option<TString<'static>>,
        chunkify: bool,
        address_qr: TString<'static>,
        case_sensitive: bool,
        account: Option<TString<'static>>,
        path: Option<TString<'static>>,
        xpubs: Obj, // TODO: replace Obj
        br_code: u16,
        br_name: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::RuntimeError(c"Not implemented"))
    }
}
