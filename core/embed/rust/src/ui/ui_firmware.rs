use crate::{
    error::Error,
    io::BinaryData,
    micropython::{gc::Gc, list::List, obj::Obj},
    strutil::TString,
};
use heapless::Vec;

use super::layout::{
    obj::{LayoutMaybeTrace, LayoutObj},
    util::RecoveryType,
};

pub const MAX_CHECKLIST_ITEMS: usize = 3;
pub const MAX_WORD_QUIZ_ITEMS: usize = 3;
pub const MAX_GROUP_SHARE_LINES: usize = 4;

pub trait FirmwareUI {
    #[allow(clippy::too_many_arguments)]
    fn confirm_action(
        title: TString<'static>,
        action: Option<TString<'static>>,
        description: Option<TString<'static>>,
        subtitle: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        verb_cancel: Option<TString<'static>>,
        hold: bool,
        hold_danger: bool,
        reverse: bool,
        prompt_screen: bool,
        prompt_title: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn confirm_address(
        title: TString<'static>,
        address: Obj, // TODO: replace Obj
        address_label: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        info_button: bool,
        chunkify: bool,
    ) -> Result<Gc<LayoutObj>, Error>; // TODO: return LayoutMaybeTrace

    #[allow(clippy::too_many_arguments)]
    fn confirm_blob(
        title: TString<'static>,
        data: Obj, // TODO: replace Obj
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
    ) -> Result<Gc<LayoutObj>, Error>; // TODO: return LayoutMaybeTrace

    fn confirm_blob_intro(
        title: TString<'static>,
        data: Obj, // TODO: replace Obj
        subtitle: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        verb_cancel: Option<TString<'static>>,
        chunkify: bool,
    ) -> Result<Gc<LayoutObj>, Error>; // TODO: return LayoutMaybeTrace

    fn confirm_homescreen(
        title: TString<'static>,
        image: BinaryData<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn confirm_coinjoin(
        max_rounds: TString<'static>,
        max_feerate: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn confirm_emphasized(
        title: TString<'static>,
        items: Obj, // TODO: replace Obj
        verb: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn confirm_fido(
        title: TString<'static>,
        app_name: TString<'static>,
        icon: Option<TString<'static>>,
        accounts: Gc<List>, // TODO: replace Gc<List>
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn confirm_firmware_update(
        description: TString<'static>,
        fingerprint: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn confirm_modify_fee(
        title: TString<'static>,
        sign: i32,
        user_fee_change: TString<'static>,
        total_fee_new: TString<'static>,
        fee_rate_amount: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn confirm_modify_output(
        sign: i32,
        amount_change: TString<'static>,
        amount_new: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn confirm_more(
        title: TString<'static>,
        button: TString<'static>,
        button_style_confirm: bool,
        items: Obj, // TODO: replace Obj
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn confirm_properties(
        title: TString<'static>,
        items: Obj, // TODO: replace Obj`
        hold: bool,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn confirm_reset_device(recovery: bool) -> Result<impl LayoutMaybeTrace, Error>;

    #[allow(clippy::too_many_arguments)]
    fn confirm_summary(
        amount: TString<'static>,
        amount_label: TString<'static>,
        fee: TString<'static>,
        fee_label: TString<'static>,
        title: Option<TString<'static>>,
        account_items: Option<Obj>, // TODO: replace Obj
        extra_items: Option<Obj>,   // TODO: replace Obj
        extra_title: Option<TString<'static>>,
        verb_cancel: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    #[allow(clippy::too_many_arguments)]
    fn confirm_value(
        title: TString<'static>,
        value: Obj, // TODO: replace Obj
        description: Option<TString<'static>>,
        subtitle: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        verb_info: Option<TString<'static>>,
        verb_cancel: Option<TString<'static>>,
        info_button: bool,
        hold: bool,
        chunkify: bool,
        text_mono: bool,
    ) -> Result<Gc<LayoutObj>, Error>; // TODO: return LayoutMaybeTrace

    fn confirm_with_info(
        title: TString<'static>,
        button: TString<'static>,
        info_button: TString<'static>,
        verb_cancel: Option<TString<'static>>,
        items: Obj, // TODO: replace Obj
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn continue_recovery_homepage(
        text: TString<'static>,
        subtext: Option<TString<'static>>,
        button: Option<TString<'static>>,
        recovery_type: RecoveryType,
        show_instructions: bool,
        remaining_shares: Option<Obj>, // TODO: replace Obj
    ) -> Result<Gc<LayoutObj>, Error>; // TODO: return LayoutMaybeTrace

    fn check_homescreen_format(image: BinaryData, accept_toif: bool) -> bool;

    #[allow(clippy::too_many_arguments)]
    fn flow_confirm_output(
        title: Option<TString<'static>>,
        subtitle: Option<TString<'static>>,
        message: Obj,        // TODO: replace Obj
        amount: Option<Obj>, // TODO: replace Obj
        chunkify: bool,
        text_mono: bool,
        account: Option<TString<'static>>,
        account_path: Option<TString<'static>>,
        br_code: u16,
        br_name: TString<'static>,
        address: Option<Obj>, // TODO: replace Obj
        address_title: Option<TString<'static>>,
        summary_items: Option<Obj>, // TODO: replace Obj
        fee_items: Option<Obj>,     // TODO: replace Obj
        summary_title: Option<TString<'static>>,
        summary_br_code: Option<u16>,
        summary_br_name: Option<TString<'static>>,
        cancel_text: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn flow_confirm_set_new_pin(
        title: TString<'static>,
        description: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    #[allow(clippy::too_many_arguments)]
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
        title_success: TString<'static>,
        br_code: u16,
        br_name: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    // TODO: this is TR specific and used only in confirm_set_new_pin
    fn multiple_pages_texts(
        title: TString<'static>,
        verb: TString<'static>,
        items: Gc<List>,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn prompt_backup() -> Result<impl LayoutMaybeTrace, Error>;

    fn request_bip39(
        prompt: TString<'static>,
        prefill_word: TString<'static>,
        can_go_back: bool,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn request_slip39(
        prompt: TString<'static>,
        prefill_word: TString<'static>,
        can_go_back: bool,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn request_number(
        title: TString<'static>,
        count: u32,
        min_count: u32,
        max_count: u32,
        description: Option<TString<'static>>,
        more_info_callback: Option<impl Fn(u32) -> TString<'static> + 'static>,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn request_pin(
        prompt: TString<'static>,
        subprompt: TString<'static>,
        allow_cancel: bool,
        warning: bool,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn request_passphrase(
        prompt: TString<'static>,
        max_len: u32,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn select_word(
        title: TString<'static>,
        description: TString<'static>,
        words: [TString<'static>; MAX_WORD_QUIZ_ITEMS],
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn select_word_count(recovery_type: RecoveryType) -> Result<impl LayoutMaybeTrace, Error>;

    fn set_brightness(current_brightness: Option<u8>) -> Result<impl LayoutMaybeTrace, Error>;

    fn show_address_details(
        qr_title: TString<'static>,
        address: TString<'static>,
        case_sensitive: bool,
        details_title: TString<'static>,
        account: Option<TString<'static>>,
        path: Option<TString<'static>>,
        xpubs: Obj, // TODO: replace Obj
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn show_checklist(
        title: TString<'static>,
        button: TString<'static>,
        active: usize,
        items: [TString<'static>; MAX_CHECKLIST_ITEMS],
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn show_danger(
        title: TString<'static>,
        description: TString<'static>,
        value: TString<'static>,
        verb_cancel: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn show_error(
        title: TString<'static>,
        button: TString<'static>,
        description: TString<'static>,
        allow_cancel: bool,
        time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error>; // TODO: return LayoutMaybeTrace

    fn show_group_share_success(
        lines: [TString<'static>; MAX_GROUP_SHARE_LINES],
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn show_homescreen(
        label: TString<'static>,
        hold: bool,
        notification: Option<TString<'static>>,
        notification_level: u8,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn show_info(
        title: TString<'static>,
        description: TString<'static>,
        button: TString<'static>,
        time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error>; // TODO: return LayoutMaybeTrace

    fn show_info_with_cancel(
        title: TString<'static>,
        items: Obj, // TODO: replace Obj
        horizontal: bool,
        chunkify: bool,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn show_lockscreen(
        label: TString<'static>,
        bootscreen: bool,
        coinjoin_authorized: bool,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn show_mismatch(title: TString<'static>) -> Result<impl LayoutMaybeTrace, Error>;

    fn show_progress(
        description: TString<'static>,
        indeterminate: bool,
        title: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn show_progress_coinjoin(
        title: TString<'static>,
        indeterminate: bool,
        time_ms: u32,
        skip_first_paint: bool,
    ) -> Result<Gc<LayoutObj>, Error>; // TODO: return LayoutMaybeTrace

    fn show_remaining_shares(
        pages_iterable: Obj, // TODO: replace Obj
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn show_share_words(
        words: Vec<TString<'static>, 33>,
        title: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    // TODO: merge with `show_share_words` instead of having specific version for
    // mercury
    fn show_share_words_mercury(
        words: Vec<TString<'static>, 33>,
        subtitle: Option<TString<'static>>,
        instructions: Obj,                     // TODO: replace Obj
        text_footer: Option<TString<'static>>, // footer description at instruction screen
        text_confirm: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn show_simple(
        text: TString<'static>,
        title: Option<TString<'static>>,
        button: Option<TString<'static>>,
    ) -> Result<Gc<LayoutObj>, Error>; // TODO: return LayoutMaybeTrace

    fn show_success(
        title: TString<'static>,
        button: TString<'static>,
        description: TString<'static>,
        allow_cancel: bool,
        time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error>; // TODO: return LayoutMaybeTrace

    fn show_wait_text(text: TString<'static>) -> Result<impl LayoutMaybeTrace, Error>;

    fn show_warning(
        title: TString<'static>,
        button: TString<'static>,
        value: TString<'static>,
        description: TString<'static>,
        allow_cancel: bool,
        danger: bool,
    ) -> Result<Gc<LayoutObj>, Error>; // TODO: return LayoutMaybeTrace

    fn tutorial() -> Result<impl LayoutMaybeTrace, Error>;
}
