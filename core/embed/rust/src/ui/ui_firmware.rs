use heapless::Vec;

use super::layout::obj::{LayoutMaybeTrace, LayoutObj};
use super::layout::util::RecoveryType;
use crate::error::Error;
use crate::io::BinaryData;
use crate::micropython::buffer::StrBuffer;
use crate::micropython::dict::Dict;
use crate::micropython::gc::Gc;
use crate::micropython::iter::IterBuf;
use crate::micropython::list::List;
use crate::micropython::map::Map;
use crate::micropython::obj::Obj;
use crate::micropython::qstr::Qstr;
use crate::micropython::util;
use crate::strutil::TString;
use crate::ui::notification::Notification;

pub const MAX_CHECKLIST_ITEMS: usize = 3;
pub const MAX_WORD_QUIZ_ITEMS: usize = 3;
pub const MAX_GROUP_SHARE_LINES: usize = 4;
pub const MAX_MENU_ITEMS: usize = 5;

pub const MAX_PAIRED_DEVICES: usize = 8; // Maximum number of paired devices in the device menu

/// Everything `show_device_menu` needs to build (or rebuild) the device menu.
///
/// Bundled into a struct rather than passed as eighteen positional arguments so
/// that the same set can be handed to a live layout again, via
/// `LayoutObj.update_params`, without repeating the parsing.
pub struct DeviceMenuParams {
    pub init_submenu_idx: Option<u8>,
    pub init_submenu_offset: i16,
    pub backup_failed: bool,
    pub backup_needed: bool,
    pub ble_enabled: bool,
    pub paired_devices: Vec<(TString<'static>, Option<[TString<'static>; 2]>), MAX_PAIRED_DEVICES>,
    pub connected_idx: Option<u8>,
    pub pin_enabled: Option<bool>,
    pub auto_lock: Option<[TString<'static>; 2]>,
    pub wipe_code_enabled: Option<bool>,
    pub backup_check_allowed: bool,
    pub device_name: Option<TString<'static>>,
    pub brightness: Option<TString<'static>>,
    pub tap_to_wake_enabled: Option<bool>,
    pub haptics_enabled: Option<bool>,
    pub led_enabled: Option<bool>,
    pub about_items: Obj,
    pub production_year: Option<TString<'static>>,
}

impl TryFrom<&Map> for DeviceMenuParams {
    type Error = Error;

    fn try_from(kwargs: &Map) -> Result<Self, Error> {
        let paired_obj: Obj = kwargs.get(Qstr::MP_QSTR_paired_devices)?;
        let mut paired_devices: Vec<(TString<'static>, Option<[TString; 2]>), MAX_PAIRED_DEVICES> =
            Vec::new();
        for device in IterBuf::new().try_iterate(paired_obj)? {
            let [mac, host_info]: [Obj; 2] = util::iter_into_array(device)?;
            let mac: TString<'static> = mac.try_into()?;
            let host_info: Option<[TString<'static>; 2]> = host_info
                .try_into_option()?
                .map(util::iter_into_array)
                .transpose()?;

            if paired_devices.push((mac, host_info)).is_err() {
                return Err(Error::OutOfRange);
            }
        }

        Ok(Self {
            init_submenu_idx: kwargs
                .get(Qstr::MP_QSTR_init_submenu_idx)?
                .try_into_option()?,
            init_submenu_offset: kwargs.get(Qstr::MP_QSTR_init_submenu_offset)?.try_into()?,
            backup_failed: kwargs.get(Qstr::MP_QSTR_backup_failed)?.try_into()?,
            backup_needed: kwargs.get(Qstr::MP_QSTR_backup_needed)?.try_into()?,
            ble_enabled: kwargs.get(Qstr::MP_QSTR_ble_enabled)?.try_into()?,
            paired_devices,
            connected_idx: kwargs.get(Qstr::MP_QSTR_connected_idx)?.try_into_option()?,
            pin_enabled: kwargs.get(Qstr::MP_QSTR_pin_enabled)?.try_into_option()?,
            auto_lock: kwargs
                .get(Qstr::MP_QSTR_auto_lock)?
                .try_into_option()?
                .map(util::iter_into_array)
                .transpose()?,
            wipe_code_enabled: kwargs
                .get(Qstr::MP_QSTR_wipe_code_enabled)?
                .try_into_option()?,
            backup_check_allowed: kwargs.get(Qstr::MP_QSTR_backup_check_allowed)?.try_into()?,
            device_name: kwargs.get(Qstr::MP_QSTR_device_name)?.try_into_option()?,
            brightness: kwargs.get(Qstr::MP_QSTR_brightness)?.try_into_option()?,
            tap_to_wake_enabled: kwargs
                .get(Qstr::MP_QSTR_tap_to_wake_enabled)?
                .try_into_option()?,
            haptics_enabled: kwargs
                .get(Qstr::MP_QSTR_haptics_enabled)?
                .try_into_option()?,
            led_enabled: kwargs.get(Qstr::MP_QSTR_led_enabled)?.try_into_option()?,
            about_items: kwargs.get(Qstr::MP_QSTR_about_items)?,
            production_year: kwargs
                .get(Qstr::MP_QSTR_production_year)?
                .try_into_option()?,
        })
    }
}

impl TryFrom<Obj> for DeviceMenuParams {
    type Error = Error;

    /// Parse the params out of a MicroPython `dict`, as handed over by
    /// `LayoutObj.update_params`.
    fn try_from(params: Obj) -> Result<Self, Error> {
        let dict: Gc<Dict> = params.try_into()?;
        dict.map().try_into()
    }
}

pub trait FirmwareUI {
    #[allow(clippy::too_many_arguments)]
    fn confirm_action(
        title: TString<'static>,
        action: Option<TString<'static>>,
        description: Option<TString<'static>>,
        subtitle: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        cancel: bool,
        verb_cancel: Option<TString<'static>>,
        hold: bool,
        hold_danger: bool,
        reverse: bool,
        prompt_screen: bool,
        prompt_title: Option<TString<'static>>,
        external_menu: bool, // TODO: will eventually replace the internal menu
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn confirm_address(
        title: TString<'static>,
        address: Obj, // TODO: replace Obj
        address_label: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        info_button: bool,
        chunkify: bool,
    ) -> Result<Gc<LayoutObj>, Error>; // TODO: return LayoutMaybeTrace

    fn confirm_trade(
        title: TString<'static>,
        subtitle: TString<'static>,
        sell_amount: Option<TString<'static>>,
        buy_amount: TString<'static>,
        back_button: bool,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    #[allow(clippy::too_many_arguments)]
    fn confirm_value(
        title: TString<'static>,
        value: Obj, // TODO: replace Obj
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
        back_button: bool,
        footer: Option<(TString<'static>, bool)>,
        external_menu: bool,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    #[allow(clippy::too_many_arguments)]
    fn confirm_value_intro(
        title: TString<'static>,
        value: Obj, // TODO: replace Obj
        subtitle: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        verb_cancel: Option<TString<'static>>,
        verb_view_all: Option<TString<'static>>,
        hold: bool,
        chunkify: bool,
    ) -> Result<Gc<LayoutObj>, Error>; // TODO: return LayoutMaybeTrace

    fn confirm_homescreen(
        title: TString<'static>,
        image: BinaryData<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn confirm_coinjoin(
        max_rounds: TString<'static>,
        max_feerate: TString<'static>,
        max_coordinator_fee_pct: TString<'static>,
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
        hold: bool,
        items: Obj, // TODO: replace Obj
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn confirm_properties(
        title: TString<'static>,
        subtitle: Option<TString<'static>>,
        items: Obj, // TODO: replace Obj`
        hold: bool,
        verb: Option<TString<'static>>,
        external_menu: bool,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn confirm_reset_device(recovery: bool) -> Result<impl LayoutMaybeTrace, Error>;

    #[allow(clippy::too_many_arguments)]
    fn confirm_summary(
        amount: Option<TString<'static>>,
        amount_label: Option<TString<'static>>,
        fee: TString<'static>,
        fee_label: TString<'static>,
        title: Option<TString<'static>>,
        account_items: Option<Obj>, // TODO: replace Obj
        account_title: Option<TString<'static>>,
        extra_items: Option<Obj>, // TODO: replace Obj
        extra_title: Option<TString<'static>>,
        verb_cancel: Option<TString<'static>>,
        back_button: bool,
        external_menu: bool, // TODO: will eventually replace the internal menu
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn confirm_with_info(
        title: TString<'static>,
        subtitle: Option<TString<'static>>,
        items: Obj, // TODO: replace Obj
        verb: TString<'static>,
        verb_info: Option<TString<'static>>,
        verb_cancel: Option<TString<'static>>,
        external_menu: bool,
    ) -> Result<Gc<LayoutObj>, Error>;

    fn continue_recovery_homepage(
        text: TString<'static>,
        subtext: Option<TString<'static>>,
        button: Option<TString<'static>>,
        recovery_type: RecoveryType,
        show_instructions: bool,
        remaining_shares: Option<Obj>, // TODO: replace Obj
    ) -> Result<Gc<LayoutObj>, Error>; // TODO: return LayoutMaybeTrace

    fn check_homescreen_format(image: BinaryData, accept_toif: bool) -> bool;

    fn flow_confirm_set_new_code(is_wipe_code: bool) -> Result<impl LayoutMaybeTrace, Error>;

    #[allow(clippy::too_many_arguments)]
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
        xpubs: Obj, // TODO: replace Obj
        br_code: u16,
        br_name: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    #[allow(clippy::too_many_arguments)]
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
    ) -> Result<impl LayoutMaybeTrace, Error>;

    // TODO: this is TR specific and used only in confirm_set_new_code
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

    fn request_duration(
        title: TString<'static>,
        duration_ms: u32,
        min_ms: u32,
        max_ms: u32,
        description: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn request_pin(
        prompt: TString<'static>,
        subprompt: TString<'static>,
        allow_cancel: bool,
        warning: bool,
        last_attempt: bool,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn request_passphrase(
        prompt: TString<'static>,
        prompt_empty: TString<'static>,
        max_len: usize,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn request_string(
        prompt: TString<'static>,
        max_len: usize,
        allow_empty: bool,
        prefill: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn select_menu(
        items: heapless::Vec<TString<'static>, MAX_MENU_ITEMS>,
        current: usize,
        cancel: Option<TString<'static>>,
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
        menu_title: Option<TString<'static>>,
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
        notification: Option<Notification>,
        lockable: bool,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn show_device_menu(params: DeviceMenuParams) -> Result<impl LayoutMaybeTrace, Error>;

    fn show_pairing_device_name(
        description: StrBuffer,
        device_name: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    #[cfg(feature = "ble")]
    fn show_ble_pairing_code(
        title: TString<'static>,
        description: TString<'static>,
        code: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    #[cfg(feature = "ble")]
    fn wait_ble_host_confirmation() -> Result<impl LayoutMaybeTrace, Error>;

    fn show_thp_pairing_code(
        title: TString<'static>,
        description: TString<'static>,
        code: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn confirm_thp_pairing(
        title: TString<'static>,
        description: (StrBuffer, Obj),
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn show_info(
        title: TString<'static>,
        description: TString<'static>,
        button: Option<(TString<'static>, bool)>,
        time_ms: u32,
        external_menu: bool, // TODO: will eventually replace the internal menu
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
        danger: bool,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn show_progress_coinjoin(
        title: TString<'static>,
        indeterminate: bool,
        time_ms: u32,
        skip_first_paint: bool,
    ) -> Result<Gc<LayoutObj>, Error>; // TODO: return LayoutMaybeTrace

    fn show_properties(
        _title: TString<'static>,
        _subtitle: Option<TString<'static>>,
        _value: Obj,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn show_remaining_shares(
        pages_iterable: Obj, // TODO: replace Obj
    ) -> Result<impl LayoutMaybeTrace, Error>;

    fn show_share_words(
        words: Vec<TString<'static>, 33>,
        title: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error>;

    // TODO: merge with `show_share_words` instead of having specific version for
    // Delizia/Eckhart UI
    fn show_share_words_extended(
        words: Vec<TString<'static>, 33>,
        subtitle: Option<TString<'static>>,
        instructions: Obj, // TODO: replace Obj
        instructions_verb: Option<TString<'static>>,
        text_footer: Option<TString<'static>>, // footer description at instruction screen
        text_confirm: TString<'static>,
        text_check: TString<'static>,
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

    fn show_warning(
        title: Option<TString<'static>>,
        button: TString<'static>,
        value: TString<'static>,
        description: TString<'static>,
        allow_cancel: bool,
        danger: bool,
    ) -> Result<Gc<LayoutObj>, Error>; // TODO: return LayoutMaybeTrace

    fn confirm_cancel() -> Result<impl LayoutMaybeTrace, Error>;

    fn tutorial() -> Result<impl LayoutMaybeTrace, Error>;
}
