use crate::{
    error::Error,
    io::BinaryData,
    micropython::{
        buffer::StrBuffer,
        gc::Gc,
        iter::IterBuf,
        list::List,
        macros::{obj_fn_0, obj_fn_1, obj_fn_kw, obj_module},
        map::Map,
        module::Module,
        obj::Obj,
        qstr::Qstr,
        util,
    },
    strutil::TString,
    trezorhal::model,
    ui::{
        backlight::BACKLIGHT_LEVELS_OBJ,
        component::Empty,
        layout::{
            base::LAYOUT_STATE,
            device_menu_result::DEVICE_MENU_RESULT,
            obj::{ComponentMsgObj, LayoutObj, ATTACH_TYPE_OBJ},
            result::{BACK, CANCELLED, CONFIRMED, INFO},
            util::{upy_disable_animation, RecoveryType},
        },
        ui_firmware::{
            FirmwareUI, MAX_CHECKLIST_ITEMS, MAX_GROUP_SHARE_LINES, MAX_PAIRED_DEVICES,
            MAX_WORD_QUIZ_ITEMS,
        },
        ModelUI,
    },
};
use heapless::Vec;

#[cfg(feature = "backlight")]
use crate::ui::display::{fade_backlight_duration, get_backlight, set_backlight};

/// Dummy implementation so that we can use `Empty` in a return type of
/// unimplemented trait function
impl ComponentMsgObj for Empty {
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, crate::error::Error> {
        unimplemented!()
    }
}

// free-standing functions exported to MicroPython mirror `trait
// UIFeaturesFirmware`
// NOTE: `disable_animation` not a part of trait UiFeaturesFirmware

extern "C" fn new_confirm_action(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let action: Option<TString> = kwargs.get(Qstr::MP_QSTR_action)?.try_into_option()?;
        let description: Option<TString> =
            kwargs.get(Qstr::MP_QSTR_description)?.try_into_option()?;
        let subtitle: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_subtitle)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let verb: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_verb)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let verb_cancel: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_verb_cancel)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;
        let hold_danger: bool = kwargs.get_or(Qstr::MP_QSTR_hold_danger, false)?;
        let reverse: bool = kwargs.get_or(Qstr::MP_QSTR_reverse, false)?;
        let prompt_screen: bool = kwargs.get_or(Qstr::MP_QSTR_prompt_screen, false)?;
        let prompt_title: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_prompt_title)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let external_menu: bool = kwargs.get_or(Qstr::MP_QSTR_external_menu, false)?;

        let layout = ModelUI::confirm_action(
            title,
            action,
            description,
            subtitle,
            verb,
            verb_cancel,
            hold,
            hold_danger,
            reverse,
            prompt_screen,
            prompt_title,
            external_menu,
        )?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_address(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let address: Obj = kwargs.get(Qstr::MP_QSTR_address)?;
        let address_label: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_address_label)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let verb: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_verb)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let info_button: bool = kwargs.get_or(Qstr::MP_QSTR_info_button, false)?;
        let chunkify: bool = kwargs.get_or(Qstr::MP_QSTR_chunkify, false)?;

        let layout_obj =
            ModelUI::confirm_address(title, address, address_label, verb, info_button, chunkify)?;
        Ok(layout_obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_trade(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let subtitle: TString = kwargs.get(Qstr::MP_QSTR_subtitle)?.try_into()?;
        let sell_amount: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_sell_amount)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let buy_amount: TString = kwargs.get(Qstr::MP_QSTR_buy_amount)?.try_into()?;
        let back_button: bool = kwargs.get_or(Qstr::MP_QSTR_back_button, false)?;
        let layout = ModelUI::confirm_trade(title, subtitle, sell_amount, buy_amount, back_button)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_value(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let value: Obj = kwargs.get(Qstr::MP_QSTR_value)?;
        let description: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_description)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let is_data: bool = kwargs.get_or(Qstr::MP_QSTR_is_data, true)?;
        let extra: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_extra)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let subtitle: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_subtitle)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let verb: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_verb)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let verb_cancel: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_verb_cancel)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let info: bool = kwargs.get_or(Qstr::MP_QSTR_info, false)?;
        let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;
        let chunkify: bool = kwargs.get_or(Qstr::MP_QSTR_chunkify, false)?;
        let page_counter: bool = kwargs.get_or(Qstr::MP_QSTR_page_counter, false)?;
        let prompt_screen: bool = kwargs.get_or(Qstr::MP_QSTR_prompt_screen, false)?;
        let cancel: bool = kwargs.get_or(Qstr::MP_QSTR_cancel, false)?;
        let back_button: bool = kwargs.get_or(Qstr::MP_QSTR_back_button, false)?;
        let warning_footer: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_warning_footer)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let external_menu: bool = kwargs.get_or(Qstr::MP_QSTR_external_menu, false)?;

        let layout = ModelUI::confirm_value(
            title,
            value,
            description,
            is_data,
            extra,
            subtitle,
            verb,
            verb_cancel,
            info,
            hold,
            chunkify,
            page_counter,
            prompt_screen,
            cancel,
            back_button,
            warning_footer,
            external_menu,
        )?;

        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_value_intro(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let value: Obj = kwargs.get(Qstr::MP_QSTR_value)?;
        let subtitle: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_subtitle)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let verb: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_verb)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let verb_cancel: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_verb_cancel)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;
        let chunkify: bool = kwargs.get_or(Qstr::MP_QSTR_chunkify, false)?;

        let layout_obj = ModelUI::confirm_value_intro(
            title,
            value,
            subtitle,
            verb,
            verb_cancel,
            hold,
            chunkify,
        )?;
        Ok(layout_obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_coinjoin(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let max_rounds: TString = kwargs.get(Qstr::MP_QSTR_max_rounds)?.try_into()?;
        let max_feerate: TString = kwargs.get(Qstr::MP_QSTR_max_feerate)?.try_into()?;

        let layout = ModelUI::confirm_coinjoin(max_rounds, max_feerate)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_emphasized(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;
        let verb: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_verb)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;

        let layout = ModelUI::confirm_emphasized(title, items, verb)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_fido(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let app_name: TString = kwargs.get(Qstr::MP_QSTR_app_name)?.try_into()?;
        let icon: Option<TString> = kwargs.get(Qstr::MP_QSTR_icon_name)?.try_into_option()?;
        let accounts: Gc<List> = kwargs.get(Qstr::MP_QSTR_accounts)?.try_into()?;

        let layout = ModelUI::confirm_fido(title, app_name, icon, accounts)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_firmware_update(
    n_args: usize,
    args: *const Obj,
    kwargs: *mut Map,
) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let description: TString = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let fingerprint: TString = kwargs.get(Qstr::MP_QSTR_fingerprint)?.try_into()?;

        let layout = ModelUI::confirm_firmware_update(description, fingerprint)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_homescreen(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let image: Obj = kwargs.get(Qstr::MP_QSTR_image)?;

        let jpeg: BinaryData = image.try_into()?;

        let layout = ModelUI::confirm_homescreen(title, jpeg)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };

    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_modify_fee(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let sign: i32 = kwargs.get(Qstr::MP_QSTR_sign)?.try_into()?;
        let user_fee_change: TString = kwargs.get(Qstr::MP_QSTR_user_fee_change)?.try_into()?;
        let total_fee_new: TString = kwargs.get(Qstr::MP_QSTR_total_fee_new)?.try_into()?;
        let fee_rate_amount: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_fee_rate_amount)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;

        let layout = ModelUI::confirm_modify_fee(
            title,
            sign,
            user_fee_change,
            total_fee_new,
            fee_rate_amount,
        )?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_modify_output(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let sign: i32 = kwargs.get(Qstr::MP_QSTR_sign)?.try_into()?;
        let amount_change: TString = kwargs.get(Qstr::MP_QSTR_amount_change)?.try_into()?;
        let amount_new: TString = kwargs.get(Qstr::MP_QSTR_amount_new)?.try_into()?;

        let layout = ModelUI::confirm_modify_output(sign, amount_change, amount_new)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_more(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let button: TString = kwargs.get(Qstr::MP_QSTR_button)?.try_into()?;
        let button_style_confirm: bool =
            kwargs.get_or(Qstr::MP_QSTR_button_style_confirm, false)?;
        let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;

        let layout = ModelUI::confirm_more(title, button, button_style_confirm, hold, items)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_properties(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let subtitle: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_subtitle)
            .and_then(Obj::try_into_option)
            .unwrap_or(None);
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;
        let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;
        let verb: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_verb)
            .and_then(Obj::try_into_option)
            .unwrap_or(None);
        let external_menu: bool = kwargs.get_or(Qstr::MP_QSTR_external_menu, false)?;

        let layout =
            ModelUI::confirm_properties(title, subtitle, items, hold, verb, external_menu)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_properties(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let subtitle: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_subtitle)
            .and_then(Obj::try_into_option)
            .unwrap_or(None);
        let value: Obj = kwargs.get(Qstr::MP_QSTR_value)?;

        let layout = ModelUI::show_properties(title, subtitle, value)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_reset_device(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let recovery: bool = kwargs.get(Qstr::MP_QSTR_recovery)?.try_into()?;

        let layout = ModelUI::confirm_reset_device(recovery)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_summary(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let amount: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_amount)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let amount_label: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_amount_label)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let fee: TString = kwargs.get(Qstr::MP_QSTR_fee)?.try_into()?;
        let fee_label: TString = kwargs.get(Qstr::MP_QSTR_fee_label)?.try_into()?;
        let title: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_title)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let account_items: Option<Obj> = kwargs
            .get(Qstr::MP_QSTR_account_items)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let account_title: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_account_title)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let extra_items: Option<Obj> = kwargs
            .get(Qstr::MP_QSTR_extra_items)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let extra_title: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_extra_title)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let verb_cancel: Option<TString<'static>> = kwargs
            .get(Qstr::MP_QSTR_verb_cancel)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let back_button: Option<bool> = kwargs
            .get(Qstr::MP_QSTR_back_button)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let external_menu: Option<bool> = kwargs
            .get(Qstr::MP_QSTR_external_menu)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;

        let layout = ModelUI::confirm_summary(
            amount,
            amount_label,
            fee,
            fee_label,
            title,
            account_items,
            account_title,
            extra_items,
            extra_title,
            verb_cancel,
            back_button.unwrap_or(false),
            external_menu.unwrap_or(false),
        )?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_with_info(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let subtitle: Option<TString<'static>> = kwargs
            .get(Qstr::MP_QSTR_subtitle)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;
        let verb: TString = kwargs.get(Qstr::MP_QSTR_verb)?.try_into()?;
        let verb_info: TString = kwargs.get(Qstr::MP_QSTR_verb_info)?.try_into()?;
        let verb_cancel: Option<TString<'static>> = kwargs
            .get(Qstr::MP_QSTR_verb_cancel)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let external_menu: bool = kwargs.get_or(Qstr::MP_QSTR_external_menu, false)?;

        let layout = ModelUI::confirm_with_info(
            title,
            subtitle,
            items,
            verb,
            verb_info,
            verb_cancel,
            external_menu,
        )?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_continue_recovery_homepage(
    n_args: usize,
    args: *const Obj,
    kwargs: *mut Map,
) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let text: TString = kwargs.get(Qstr::MP_QSTR_text)?.try_into()?; // #shares entered
        let subtext: Option<TString> = kwargs.get(Qstr::MP_QSTR_subtext)?.try_into_option()?; // #shares remaining
        let button: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_button)
            .and_then(Obj::try_into_option)
            .unwrap_or(None);
        let recovery_type: RecoveryType = kwargs.get(Qstr::MP_QSTR_recovery_type)?.try_into()?;
        let show_instructions: bool = kwargs.get_or(Qstr::MP_QSTR_show_instructions, false)?;
        let remaining_shares: Option<Obj> = kwargs
            .get(Qstr::MP_QSTR_remaining_shares)?
            .try_into_option()?; // info about remaining shares

        let obj = ModelUI::continue_recovery_homepage(
            text,
            subtext,
            button,
            recovery_type,
            show_instructions,
            remaining_shares,
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_flow_confirm_output(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: Option<TString> = kwargs.get(Qstr::MP_QSTR_title)?.try_into_option()?;
        let subtitle: Option<TString> = kwargs.get(Qstr::MP_QSTR_subtitle)?.try_into_option()?;
        let extra: Option<TString> = kwargs.get(Qstr::MP_QSTR_extra)?.try_into_option()?;
        let description: Option<TString> =
            kwargs.get(Qstr::MP_QSTR_description)?.try_into_option()?;
        let message: TString = kwargs.get(Qstr::MP_QSTR_message)?.try_into()?;
        let chunkify: bool = kwargs.get_or(Qstr::MP_QSTR_chunkify, false)?;
        let text_mono: bool = kwargs.get_or(Qstr::MP_QSTR_text_mono, true)?;
        let account_title: TString = kwargs.get(Qstr::MP_QSTR_account_title)?.try_into()?;
        let account: Option<TString> = kwargs.get(Qstr::MP_QSTR_account)?.try_into_option()?;
        let account_path: Option<TString> =
            kwargs.get(Qstr::MP_QSTR_account_path)?.try_into_option()?;
        let br_code: u16 = kwargs.get(Qstr::MP_QSTR_br_code)?.try_into()?;
        let br_name: TString = kwargs.get(Qstr::MP_QSTR_br_name)?.try_into()?;

        let address_item: Option<Obj> =
            kwargs.get(Qstr::MP_QSTR_address_item)?.try_into_option()?;
        let extra_item: Option<Obj> = kwargs.get(Qstr::MP_QSTR_extra_item)?.try_into_option()?;
        let summary_items: Option<Obj> =
            kwargs.get(Qstr::MP_QSTR_summary_items)?.try_into_option()?;
        let fee_items: Option<Obj> = kwargs.get(Qstr::MP_QSTR_fee_items)?.try_into_option()?;
        let summary_title: Option<TString> =
            kwargs.get(Qstr::MP_QSTR_summary_title)?.try_into_option()?;
        let summary_br_code: Option<u16> = kwargs
            .get(Qstr::MP_QSTR_summary_br_code)?
            .try_into_option()?;
        let summary_br_name: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_summary_br_name)?
            .try_into_option()?;
        let cancel_text: Option<TString> =
            kwargs.get(Qstr::MP_QSTR_cancel_text)?.try_into_option()?;

        let layout = ModelUI::flow_confirm_output(
            title,
            subtitle,
            description,
            extra,
            message,
            chunkify,
            text_mono,
            account_title,
            account,
            account_path,
            br_code,
            br_name,
            address_item,
            extra_item,
            summary_items,
            fee_items,
            summary_title,
            summary_br_code,
            summary_br_name,
            cancel_text,
        )?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_flow_confirm_set_new_code(
    n_args: usize,
    args: *const Obj,
    kwargs: *mut Map,
) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let is_wipe_code: bool = kwargs.get(Qstr::MP_QSTR_is_wipe_code)?.try_into()?;

        let layout = ModelUI::flow_confirm_set_new_code(is_wipe_code)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_flow_get_address(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let subtitle: Option<TString> = kwargs.get(Qstr::MP_QSTR_subtitle)?.try_into_option()?;
        let description: Option<TString> =
            kwargs.get(Qstr::MP_QSTR_description)?.try_into_option()?;
        let hint: Option<TString> = kwargs.get(Qstr::MP_QSTR_hint)?.try_into_option()?;
        let address: TString = kwargs.get(Qstr::MP_QSTR_address)?.try_into()?;
        let chunkify: bool = kwargs.get_or(Qstr::MP_QSTR_chunkify, false)?;
        let address_qr: TString = kwargs.get(Qstr::MP_QSTR_address_qr)?.try_into()?;
        let case_sensitive: bool = kwargs.get(Qstr::MP_QSTR_case_sensitive)?.try_into()?;
        let account: Option<TString> = kwargs.get(Qstr::MP_QSTR_account)?.try_into_option()?;
        let path: Option<TString> = kwargs.get(Qstr::MP_QSTR_path)?.try_into_option()?;
        let xpubs: Obj = kwargs.get(Qstr::MP_QSTR_xpubs)?;
        let br_code: u16 = kwargs.get(Qstr::MP_QSTR_br_code)?.try_into()?;
        let br_name: TString = kwargs.get(Qstr::MP_QSTR_br_name)?.try_into()?;

        let layout = ModelUI::flow_get_address(
            address,
            title,
            subtitle,
            description,
            hint,
            chunkify,
            address_qr,
            case_sensitive,
            account,
            path,
            xpubs,
            br_code,
            br_name,
        )?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_flow_get_pubkey(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let subtitle: Option<TString> = kwargs.get(Qstr::MP_QSTR_subtitle)?.try_into_option()?;
        let hint: Option<TString> = kwargs.get(Qstr::MP_QSTR_hint)?.try_into_option()?;
        let pubkey: TString = kwargs.get(Qstr::MP_QSTR_pubkey)?.try_into()?;
        let pubkey_qr: TString = kwargs.get(Qstr::MP_QSTR_pubkey_qr)?.try_into()?;
        let account: Option<TString> = kwargs.get(Qstr::MP_QSTR_account)?.try_into_option()?;
        let path: Option<TString> = kwargs.get(Qstr::MP_QSTR_path)?.try_into_option()?;
        let br_code: u16 = kwargs.get(Qstr::MP_QSTR_br_code)?.try_into()?;
        let br_name: TString = kwargs.get(Qstr::MP_QSTR_br_name)?.try_into()?;

        let layout = ModelUI::flow_get_pubkey(
            pubkey, title, subtitle, hint, pubkey_qr, account, path, br_code, br_name,
        )?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_multiple_pages_texts(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let verb: TString = kwargs.get(Qstr::MP_QSTR_verb)?.try_into()?;
        let items: Gc<List> = kwargs.get(Qstr::MP_QSTR_items)?.try_into()?;

        let layout = ModelUI::multiple_pages_texts(title, verb, items)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_prompt_backup() -> Obj {
    let block = || {
        let layout = ModelUI::prompt_backup()?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn new_request_bip39(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let prompt: TString = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let prefill_word: TString = kwargs.get(Qstr::MP_QSTR_prefill_word)?.try_into()?;
        let can_go_back: bool = kwargs.get(Qstr::MP_QSTR_can_go_back)?.try_into()?;

        let layout = ModelUI::request_bip39(prompt, prefill_word, can_go_back)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_slip39(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let prompt: TString = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let prefill_word: TString = kwargs.get(Qstr::MP_QSTR_prefill_word)?.try_into()?;
        let can_go_back: bool = kwargs.get(Qstr::MP_QSTR_can_go_back)?.try_into()?;

        let layout = ModelUI::request_slip39(prompt, prefill_word, can_go_back)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_number(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let count: u32 = kwargs.get(Qstr::MP_QSTR_count)?.try_into()?;
        let min_count: u32 = kwargs.get(Qstr::MP_QSTR_min_count)?.try_into()?;
        let max_count: u32 = kwargs.get(Qstr::MP_QSTR_max_count)?.try_into()?;
        let description: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_description)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let more_info_callback: Option<Obj> = kwargs
            .get(Qstr::MP_QSTR_more_info_callback)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;

        let more_info_cb = more_info_callback.map(|callback| {
            move |n: u32| {
                let text = callback.call_with_n_args(&[n.try_into().unwrap()]).unwrap();
                TString::try_from(text).unwrap()
            }
        });

        let layout = ModelUI::request_number(
            title,
            count,
            min_count,
            max_count,
            description,
            more_info_cb,
        )?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_duration(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let duration_ms: u32 = kwargs.get(Qstr::MP_QSTR_duration_ms)?.try_into()?;
        let min_ms: u32 = kwargs.get(Qstr::MP_QSTR_min_ms)?.try_into()?;
        let max_ms: u32 = kwargs.get(Qstr::MP_QSTR_max_ms)?.try_into()?;
        let description: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_description)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;

        let layout = ModelUI::request_duration(title, duration_ms, min_ms, max_ms, description)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_pin(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let prompt: TString = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let attempts: TString = kwargs.get(Qstr::MP_QSTR_attempts)?.try_into()?;
        let allow_cancel: bool = kwargs.get_or(Qstr::MP_QSTR_allow_cancel, true)?;
        let wrong_pin: bool = kwargs.get_or(Qstr::MP_QSTR_wrong_pin, false)?;
        let last_attempt: bool = kwargs.get_or(Qstr::MP_QSTR_last_attempt, false)?;

        let layout = ModelUI::request_pin(prompt, attempts, allow_cancel, wrong_pin, last_attempt)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_passphrase(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let prompt: TString = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let prompt_empty: TString = kwargs.get(Qstr::MP_QSTR_prompt_empty)?.try_into()?;
        let max_len: usize = kwargs.get(Qstr::MP_QSTR_max_len)?.try_into()?;

        let layout = ModelUI::request_passphrase(prompt, prompt_empty, max_len)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_string(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let prompt: TString = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let max_len: usize = kwargs.get(Qstr::MP_QSTR_max_len)?.try_into()?;
        let allow_empty: bool = kwargs.get(Qstr::MP_QSTR_allow_empty)?.try_into()?;
        let prefill: Option<TString> = kwargs.get(Qstr::MP_QSTR_prefill)?.try_into_option()?;

        let layout = ModelUI::request_string(prompt, max_len, allow_empty, prefill)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_select_menu(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let items_iterable: Obj = kwargs.get(Qstr::MP_QSTR_items)?;
        let items = util::iter_into_vec(items_iterable)?;
        let current = kwargs.get(Qstr::MP_QSTR_current)?.try_into()?;
        let cancel = kwargs
            .get(Qstr::MP_QSTR_cancel)
            .and_then(Obj::try_into_option)
            .unwrap_or(None);

        let layout = ModelUI::select_menu(items, current, cancel)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_select_word(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: TString = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let words_iterable: Obj = kwargs.get(Qstr::MP_QSTR_words)?;
        let words: [TString<'static>; MAX_WORD_QUIZ_ITEMS] = util::iter_into_array(words_iterable)?;

        let layout = ModelUI::select_word(title, description, words)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_select_word_count(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let recovery_type: RecoveryType = kwargs.get(Qstr::MP_QSTR_recovery_type)?.try_into()?;

        let layout = ModelUI::select_word_count(recovery_type)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_set_brightness(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let current: Option<u8> = kwargs.get(Qstr::MP_QSTR_current)?.try_into_option()?;

        let layout = ModelUI::set_brightness(current)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_address_details(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let qr_title: TString<'static> = kwargs.get(Qstr::MP_QSTR_qr_title)?.try_into()?;
        let details_title: TString = kwargs.get(Qstr::MP_QSTR_details_title)?.try_into()?;
        let address: TString = kwargs.get(Qstr::MP_QSTR_address)?.try_into()?;
        let case_sensitive: bool = kwargs.get(Qstr::MP_QSTR_case_sensitive)?.try_into()?;
        let account: Option<TString> = kwargs.get(Qstr::MP_QSTR_account)?.try_into_option()?;
        let path: Option<TString> = kwargs.get(Qstr::MP_QSTR_path)?.try_into_option()?;
        let xpubs: Obj = kwargs.get(Qstr::MP_QSTR_xpubs)?;

        let layout = ModelUI::show_address_details(
            qr_title,
            address,
            case_sensitive,
            details_title,
            account,
            path,
            xpubs,
        )?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_checklist(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let button: TString = kwargs.get(Qstr::MP_QSTR_button)?.try_into()?;
        let active: usize = kwargs.get(Qstr::MP_QSTR_active)?.try_into()?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;

        let items: [TString<'static>; MAX_CHECKLIST_ITEMS] = util::iter_into_array(items)?;

        let layout = ModelUI::show_checklist(title, button, active, items)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_danger(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: TString = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let value: TString = kwargs.get_or(Qstr::MP_QSTR_value, "".into())?;
        let menu_title: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_menu_title)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let verb_cancel: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_verb_cancel)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;

        let layout = ModelUI::show_danger(title, description, value, menu_title, verb_cancel)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_error(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let button: TString = kwargs.get(Qstr::MP_QSTR_button)?.try_into()?;
        let description: TString = kwargs.get_or(Qstr::MP_QSTR_description, "".into())?;
        let allow_cancel: bool = kwargs.get_or(Qstr::MP_QSTR_allow_cancel, true)?;
        let time_ms: u32 = kwargs.get_or(Qstr::MP_QSTR_time_ms, 0)?;

        let layout = ModelUI::show_error(title, button, description, allow_cancel, time_ms)?;
        Ok(layout.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_group_share_success(
    n_args: usize,
    args: *const Obj,
    kwargs: *mut Map,
) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let lines_iterable: Obj = kwargs.get(Qstr::MP_QSTR_lines)?;
        let lines: [TString; MAX_GROUP_SHARE_LINES] = util::iter_into_array(lines_iterable)?;

        let layout = ModelUI::show_group_share_success(lines)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_homescreen(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let label: TString<'static> = kwargs.get(Qstr::MP_QSTR_label)?.try_into()?;
        let notification: Option<TString<'static>> =
            kwargs.get(Qstr::MP_QSTR_notification)?.try_into_option()?;
        let notification_level: u8 = kwargs.get_or(Qstr::MP_QSTR_notification_level, 0)?;
        let lockable: bool = kwargs.get(Qstr::MP_QSTR_lockable)?.try_into()?;
        let skip_first_paint: bool = kwargs.get(Qstr::MP_QSTR_skip_first_paint)?.try_into()?;

        let layout = ModelUI::show_homescreen(label, notification, notification_level, lockable)?;
        let layout_obj = LayoutObj::new_root(layout)?;
        if skip_first_paint {
            layout_obj.skip_first_paint();
        }
        Ok(layout_obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_device_menu(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let init_submenu_idx: Option<u8> = kwargs
            .get(Qstr::MP_QSTR_init_submenu_idx)?
            .try_into_option()?;
        let backup_failed: bool = kwargs.get(Qstr::MP_QSTR_backup_failed)?.try_into()?;
        let backup_needed: bool = kwargs.get(Qstr::MP_QSTR_backup_needed)?.try_into()?;
        let ble_enabled: bool = kwargs.get(Qstr::MP_QSTR_ble_enabled)?.try_into()?;
        let paired_obj: Obj = kwargs.get(Qstr::MP_QSTR_paired_devices)?;
        let mut paired_devices: heapless::Vec<
            (TString<'static>, Option<[TString; 2]>),
            MAX_PAIRED_DEVICES,
        > = heapless::Vec::new();
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
        let connected_idx: Option<u8> =
            kwargs.get(Qstr::MP_QSTR_connected_idx)?.try_into_option()?;
        let pin_enabled: Option<bool> = kwargs.get(Qstr::MP_QSTR_pin_enabled)?.try_into_option()?;
        let auto_lock: Option<[TString; 2]> = kwargs
            .get(Qstr::MP_QSTR_auto_lock)?
            .try_into_option()?
            .map(util::iter_into_array)
            .transpose()?;
        let wipe_code_enabled: Option<bool> = kwargs
            .get(Qstr::MP_QSTR_wipe_code_enabled)?
            .try_into_option()?;
        let backup_check_allowed: bool =
            kwargs.get(Qstr::MP_QSTR_backup_check_allowed)?.try_into()?;
        let device_name: Option<TString> =
            kwargs.get(Qstr::MP_QSTR_device_name)?.try_into_option()?;
        let brightness: Option<TString> =
            kwargs.get(Qstr::MP_QSTR_brightness)?.try_into_option()?;
        let haptics_enabled: Option<bool> = kwargs
            .get(Qstr::MP_QSTR_haptics_enabled)?
            .try_into_option()?;
        let led_enabled: Option<bool> = kwargs.get(Qstr::MP_QSTR_led_enabled)?.try_into_option()?;
        let about_items: Obj = kwargs.get(Qstr::MP_QSTR_about_items)?;
        let layout = ModelUI::show_device_menu(
            init_submenu_idx,
            backup_failed,
            backup_needed,
            ble_enabled,
            paired_devices,
            connected_idx,
            pin_enabled,
            auto_lock,
            wipe_code_enabled,
            backup_check_allowed,
            device_name,
            brightness,
            haptics_enabled,
            led_enabled,
            about_items,
        )?;

        let layout_obj = LayoutObj::new_root(layout)?;
        Ok(layout_obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_pairing_device_name(
    n_args: usize,
    args: *const Obj,
    kwargs: *mut Map,
) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let description: StrBuffer = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let device_name: TString = kwargs.get(Qstr::MP_QSTR_device_name)?.try_into()?;
        let layout = ModelUI::show_pairing_device_name(description, device_name)?;
        let layout_obj = LayoutObj::new_root(layout)?;
        Ok(layout_obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

// Prefix parameters with `_` to avoid unused variable warning when building
// without "ble".
extern "C" fn new_wait_ble_host_confirmation(
    _n_args: usize,
    _args: *const Obj,
    _kwargs: *mut Map,
) -> Obj {
    #[cfg(feature = "ble")]
    {
        let block = move |_args: &[Obj], _kwargs: &Map| {
            let layout = ModelUI::wait_ble_host_confirmation()?;
            let layout_obj = LayoutObj::new_root(layout)?;
            Ok(layout_obj.into())
        };
        unsafe { util::try_with_args_and_kwargs(_n_args, _args, _kwargs, block) }
    }

    #[cfg(not(feature = "ble"))]
    unimplemented!()
}

// Prefix parameters with `_` to avoid unused variable warning when building
// without "ble".
extern "C" fn new_show_ble_pairing_code(
    _n_args: usize,
    _args: *const Obj,
    _kwargs: *mut Map,
) -> Obj {
    #[cfg(feature = "ble")]
    {
        let block = move |_args: &[Obj], kwargs: &Map| {
            let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
            let description: TString = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
            let code: TString = kwargs.get(Qstr::MP_QSTR_code)?.try_into()?;
            let layout = ModelUI::show_ble_pairing_code(title, description, code)?;
            let layout_obj = LayoutObj::new_root(layout)?;
            Ok(layout_obj.into())
        };
        unsafe { util::try_with_args_and_kwargs(_n_args, _args, _kwargs, block) }
    }

    #[cfg(not(feature = "ble"))]
    unimplemented!()
}

extern "C" fn new_show_thp_pairing_code(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: TString = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let code: TString = kwargs.get(Qstr::MP_QSTR_code)?.try_into()?;
        let layout = ModelUI::show_thp_pairing_code(title, description, code)?;
        let layout_obj = LayoutObj::new_root(layout)?;
        Ok(layout_obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_thp_pairing(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let fmt: StrBuffer = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let args: Obj = kwargs.get(Qstr::MP_QSTR_args)?;
        let layout = ModelUI::confirm_thp_pairing(title, (fmt, args))?;
        let layout_obj = LayoutObj::new_root(layout)?;
        Ok(layout_obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_info(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: TString = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let button: TString = kwargs.get_or(Qstr::MP_QSTR_button, TString::empty())?;
        let time_ms: u32 = kwargs.get_or(Qstr::MP_QSTR_time_ms, 0)?.try_into()?;

        let obj = ModelUI::show_info(title, description, button, time_ms)?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_info_with_cancel(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;
        let horizontal: bool = kwargs.get_or(Qstr::MP_QSTR_horizontal, false)?;
        let chunkify: bool = kwargs.get_or(Qstr::MP_QSTR_chunkify, false)?;

        let layout = ModelUI::show_info_with_cancel(title, items, horizontal, chunkify)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_lockscreen(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let label: TString<'static> = kwargs
            .get(Qstr::MP_QSTR_label)?
            .try_into_option()?
            .unwrap_or_else(|| model::FULL_NAME.into());
        let bootscreen: bool = kwargs.get(Qstr::MP_QSTR_bootscreen)?.try_into()?;
        let coinjoin_authorized: bool = kwargs.get_or(Qstr::MP_QSTR_coinjoin_authorized, false)?;
        let skip_first_paint: bool = kwargs.get(Qstr::MP_QSTR_skip_first_paint)?.try_into()?;

        let layout = ModelUI::show_lockscreen(label, bootscreen, coinjoin_authorized)?;
        let layout_obj = LayoutObj::new_root(layout)?;
        if skip_first_paint {
            layout_obj.skip_first_paint();
        }
        Ok(layout_obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_mismatch(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;

        let layout = ModelUI::show_mismatch(title)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_progress(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let description: TString = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let indeterminate: bool = kwargs.get_or(Qstr::MP_QSTR_indeterminate, false)?;
        let title: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_title)
            .and_then(Obj::try_into_option)
            .unwrap_or(None);
        let danger: bool = kwargs.get_or(Qstr::MP_QSTR_danger, false)?;

        let layout = ModelUI::show_progress(description, indeterminate, title, danger)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_progress_coinjoin(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let indeterminate: bool = kwargs.get_or(Qstr::MP_QSTR_indeterminate, false)?;
        let time_ms: u32 = kwargs.get_or(Qstr::MP_QSTR_time_ms, 0)?;
        let skip_first_paint: bool = kwargs.get_or(Qstr::MP_QSTR_skip_first_paint, false)?;

        let obj = ModelUI::show_progress_coinjoin(title, indeterminate, time_ms, skip_first_paint)?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_remaining_shares(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let pages_iterable: Obj = kwargs.get(Qstr::MP_QSTR_pages)?;
        let layout = ModelUI::show_remaining_shares(pages_iterable)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_share_words(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let words: Obj = kwargs.get(Qstr::MP_QSTR_words)?;
        let title: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_title)
            .and_then(Obj::try_into_option)
            .unwrap_or(None);

        let words: Vec<TString, 33> = util::iter_into_vec(words)?;

        let layout = ModelUI::show_share_words(words, title)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_share_words_extended(
    n_args: usize,
    args: *const Obj,
    kwargs: *mut Map,
) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let words: Obj = kwargs.get(Qstr::MP_QSTR_words)?;
        let subtitle: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_subtitle)
            .and_then(Obj::try_into_option)
            .unwrap_or(None);
        let instructions: Obj = kwargs.get(Qstr::MP_QSTR_instructions)?;
        let instructions_verb: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_instructions_verb)
            .and_then(Obj::try_into_option)
            .unwrap_or(None);
        let text_footer: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_text_footer)
            .and_then(Obj::try_into_option)
            .unwrap_or(None);
        let text_confirm: TString = kwargs.get(Qstr::MP_QSTR_text_confirm)?.try_into()?;
        let text_check: TString = kwargs.get(Qstr::MP_QSTR_text_check)?.try_into()?;

        let words: Vec<TString, 33> = util::iter_into_vec(words)?;

        let layout = ModelUI::show_share_words_extended(
            words,
            subtitle,
            instructions,
            instructions_verb,
            text_footer,
            text_confirm,
            text_check,
        )?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_simple(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let text: TString = kwargs.get(Qstr::MP_QSTR_text)?.try_into()?;
        let title: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_title)
            .and_then(Obj::try_into_option)
            .unwrap_or(None);
        let button: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_button)
            .and_then(Obj::try_into_option)
            .unwrap_or(None);

        let obj = ModelUI::show_simple(text, title, button)?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_success(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let button: TString = kwargs.get(Qstr::MP_QSTR_button)?.try_into()?;
        let description: TString = kwargs.get_or(Qstr::MP_QSTR_description, TString::empty())?;
        let allow_cancel: bool = kwargs.get_or(Qstr::MP_QSTR_allow_cancel, false)?;
        let time_ms: u32 = kwargs.get_or(Qstr::MP_QSTR_time_ms, 0)?;

        let layout = ModelUI::show_success(title, button, description, allow_cancel, time_ms)?;
        Ok(layout.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_wait_text(message: Obj) -> Obj {
    let block = || {
        let message: TString<'static> = message.try_into()?;

        let layout = ModelUI::show_wait_text(message)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn new_show_warning(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let button: TString = kwargs.get(Qstr::MP_QSTR_button)?.try_into()?;
        let value: TString = kwargs.get_or(Qstr::MP_QSTR_value, "".into())?;
        let description: TString = kwargs.get_or(Qstr::MP_QSTR_description, "".into())?;
        let allow_cancel: bool = kwargs.get_or(Qstr::MP_QSTR_allow_cancel, true)?;
        let danger: bool = kwargs.get_or(Qstr::MP_QSTR_danger, false)?;

        let layout =
            ModelUI::show_warning(title, button, value, description, allow_cancel, danger)?;
        Ok(layout.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_tutorial(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], _kwargs: &Map| {
        let layout = ModelUI::tutorial()?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

pub extern "C" fn upy_check_homescreen_format(data: Obj) -> Obj {
    let block = || {
        let buffer = data.try_into()?;
        Ok(ModelUI::check_homescreen_format(buffer, false).into())
    };

    unsafe { util::try_or_raise(block) }
}

pub extern "C" fn upy_backlight_get() -> Obj {
    let block = || {
        #[cfg(feature = "backlight")]
        {
            let backlight_level = get_backlight();
            Ok(Obj::from(backlight_level))
        }
        #[cfg(not(feature = "backlight"))]
        {
            Err(crate::error::Error::RuntimeError(
                c"Backlight not supported",
            ))
        }
    };
    unsafe { util::try_or_raise(block) }
}

pub extern "C" fn upy_backlight_set(_level: Obj) -> Obj {
    let block = || {
        #[cfg(feature = "backlight")]
        set_backlight(_level.try_into()?);
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

pub extern "C" fn upy_backlight_fade(_level: Obj) -> Obj {
    let block = || {
        #[cfg(feature = "backlight")]
        fade_backlight_duration(_level.try_into()?, 150);
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
pub static mp_module_trezorui_api: Module = obj_module! {
    /// from trezor import utils
    /// from trezor.enums import ButtonRequestType, RecoveryType
    ///
    /// PropertyType = tuple[str | None, StrOrBytes | None, bool | None]
    /// T = TypeVar("T")
    ///
    /// class LayoutObj(Generic[T]):
    ///     """Representation of a Rust-based layout object.
    ///     see `trezor::ui::layout::obj::LayoutObj`.
    ///     """
    ///
    ///     def attach_timer_fn(
    ///         self, fn: Callable[[int, int], None], attach_type: AttachType | None
    ///     ) -> LayoutState | None:
    ///         """Attach a timer setter function.
    ///
    ///         The layout object can call the timer setter with two arguments,
    ///         `token` and `duration_ms`. When `duration_ms` elapses, the layout object
    ///         expects a callback to `self.timer(token)`.
    ///         """
    ///
    ///     if utils.USE_TOUCH:
    ///         def touch_event(self, event: int, x: int, y: int) -> LayoutState | None:
    ///             """Receive a touch event `event` at coordinates `x`, `y`."""
    ///
    ///     if utils.USE_BUTTON:
    ///         def button_event(self, event: int, button: int) -> LayoutState | None:
    ///             """Receive a button event `event` for button `button`."""
    ///
    ///     if utils.USE_BLE:
    ///         def ble_event(self, event: int, data: bytes) -> LayoutState | None:
    ///             """Receive a BLE events."""
    ///
    ///     if utils.USE_POWER_MANAGER:
    ///         def pm_event(self, flags: int) -> LayoutState | None:
    ///             """Receive a power management event with packed flags."""
    ///
    ///     def progress_event(self, value: int, description: str) -> LayoutState | None:
    ///         """Receive a progress event."""
    ///
    ///     def usb_event(self, connected: bool) -> LayoutState | None:
    ///         """Receive a USB connect/disconnect event."""
    ///
    ///     def timer(self, token: int) -> LayoutState | None:
    ///         """Callback for the timer set by `attach_timer_fn`.
    ///
    ///         This function should be called by the executor after the corresponding
    ///         duration elapses.
    ///         """
    ///
    ///     def paint(self) -> bool:
    ///         """Paint the layout object on screen.
    ///
    ///         Will only paint updated parts of the layout as required.
    ///         Returns True if any painting actually happened.
    ///         """
    ///
    ///     def request_complete_repaint(self) -> None:
    ///         """Request a complete repaint of the screen.
    ///
    ///         Does not repaint the screen, a subsequent call to `paint()` is required.
    ///         """
    ///
    ///     if __debug__:
    ///         def trace(self, tracer: Callable[[str], None]) -> None:
    ///             """Generate a JSON trace of the layout object.
    ///
    ///             The JSON can be emitted as a sequence of calls to `tracer`, each of
    ///             which is not necessarily a valid JSON chunk. The caller must
    ///             reassemble the chunks to get a sensible result.
    ///             """
    ///
    ///         def bounds(self) -> None:
    ///             """Paint bounds of individual components on screen."""
    ///
    ///     def page_count(self) -> int:
    ///         """Return the number of pages in the layout object."""
    ///
    ///     def button_request(self) -> tuple[ButtonRequestType, str] | None:
    ///         """Return (code, type) of button request made during the last event or timer pass."""
    ///
    ///     def get_transition_out(self) -> AttachType:
    ///         """Return the transition type."""
    ///
    ///     def return_value(self) -> T:
    ///         """Retrieve the return value of the layout object."""
    ///
    ///     def __del__(self) -> None:
    ///         """Calls drop on contents of the root component."""
    ///
    /// class UiResult:
    ///     """Result of a UI operation."""
    ///     pass
    ///
    /// mock:global
    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezorui_api.to_obj(),

    /// CONFIRMED: UiResult
    Qstr::MP_QSTR_CONFIRMED => CONFIRMED.as_obj(),

    /// BACK: UiResult
    Qstr::MP_QSTR_BACK => BACK.as_obj(),

    /// CANCELLED: UiResult
    Qstr::MP_QSTR_CANCELLED => CANCELLED.as_obj(),

    /// INFO: UiResult
    Qstr::MP_QSTR_INFO => INFO.as_obj(),

    /// def check_homescreen_format(data: AnyBytes) -> bool:
    ///     """Check homescreen format and dimensions."""
    Qstr::MP_QSTR_check_homescreen_format => obj_fn_1!(upy_check_homescreen_format).as_obj(),

    /// def disable_animation(disable: bool) -> None:
    ///     """Disable animations, debug builds only."""
    Qstr::MP_QSTR_disable_animation => obj_fn_1!(upy_disable_animation).as_obj(),

    /// def backlight_get() -> int:
    ///     """Get currently set backlight level. Returns None if backlight is not supported."""
    Qstr::MP_QSTR_backlight_get => obj_fn_0!(upy_backlight_get).as_obj(),

    /// def backlight_set(level: int) -> None:
    ///     """Set backlight to desired level."""
    Qstr::MP_QSTR_backlight_set => obj_fn_1!(upy_backlight_set).as_obj(),

    /// def backlight_fade(level: int) -> None:
    ///     """Fade backlight to desired level."""
    Qstr::MP_QSTR_backlight_fade => obj_fn_1!(upy_backlight_fade).as_obj(),

    /// def confirm_action(
    ///     *,
    ///     title: str,
    ///     action: str | None,
    ///     description: str | None,
    ///     subtitle: str | None = None,
    ///     verb: str | None = None,
    ///     verb_cancel: str | None = None,
    ///     hold: bool = False,
    ///     hold_danger: bool = False,
    ///     reverse: bool = False,
    ///     prompt_screen: bool = False,
    ///     prompt_title: str | None = None,
    ///     external_menu: bool = False,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm action."""
    Qstr::MP_QSTR_confirm_action => obj_fn_kw!(0, new_confirm_action).as_obj(),

    /// def confirm_address(
    ///     *,
    ///     title: str,
    ///     address: StrOrBytes,
    ///     address_label: str | None = None,
    ///     verb: str | None = None,
    ///     info_button: bool = False,
    ///     chunkify: bool = False,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm address."""
    Qstr::MP_QSTR_confirm_address => obj_fn_kw!(0, new_confirm_address).as_obj(),

    /// def confirm_trade(
    ///     *,
    ///     title: str,
    ///     subtitle: str,
    ///     sell_amount: str | None,
    ///     buy_amount: str,
    ///     back_button: bool = False,
    /// ) -> LayoutObj[UiResult]:
    ///     """A general way to confirm a "trade", which consists of
    ///     two amounts - one that is sold and what that is bought."""
    Qstr::MP_QSTR_confirm_trade => obj_fn_kw!(0, new_confirm_trade).as_obj(),

    /// def confirm_value(
    ///     *,
    ///     title: str,
    ///     value: StrOrBytes,
    ///     description: str | None,
    ///     is_data: bool = True,
    ///     extra: str | None = None,
    ///     subtitle: str | None = None,
    ///     verb: str | None = None,
    ///     verb_cancel: str | None = None,
    ///     info: bool = False,
    ///     hold: bool = False,
    ///     chunkify: bool = False,
    ///     page_counter: bool = False,
    ///     prompt_screen: bool = False,
    ///     cancel: bool = False,
    ///     back_button: bool = False,
    ///     warning_footer: str | None = None,
    ///     external_menu: bool = False,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm a generic piece of information on the screen.
    ///     The value can either be human readable text (`is_data=False`)
    ///     or something else - like an address or a blob of data.
    ///     The difference between the two kinds of values
    ///     is both in the font and in the linebreak strategy."""
    Qstr::MP_QSTR_confirm_value => obj_fn_kw!(0, new_confirm_value).as_obj(),

    /// def confirm_value_intro(
    ///     *,
    ///     title: str,
    ///     value: StrOrBytes,
    ///     subtitle: str | None = None,
    ///     verb: str | None = None,
    ///     verb_cancel: str | None = None,
    ///     hold: bool = False,
    ///     chunkify: bool = False,
    /// ) -> LayoutObj[UiResult]:
    ///     """Similar to `confirm_value`, but only the first page is shown.
    ///     This function is intended as a building block for a higher level `confirm_blob`
    ///     abstraction which can paginate the blob, show just the first page
    ///     and instruct the user to view the complete blob if they wish."""
    Qstr::MP_QSTR_confirm_value_intro => obj_fn_kw!(0, new_confirm_value_intro).as_obj(),

    /// def confirm_coinjoin(
    ///     *,
    ///     max_rounds: str,
    ///     max_feerate: str,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm coinjoin authorization."""
    Qstr::MP_QSTR_confirm_coinjoin => obj_fn_kw!(0, new_confirm_coinjoin).as_obj(),

    /// def confirm_emphasized(
    ///     *,
    ///     title: str,
    ///     items: Iterable[str | tuple[bool, str]],
    ///     verb: str | None = None,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm formatted text that has been pre-split in python. For tuples
    ///     the first component is a bool indicating whether this part is emphasized."""
    Qstr::MP_QSTR_confirm_emphasized => obj_fn_kw!(0, new_confirm_emphasized).as_obj(),

    /// def confirm_fido(
    ///     *,
    ///     title: str,
    ///     app_name: str,
    ///     icon_name: str | None,
    ///     accounts: Sequence[str | None],
    /// ) -> LayoutObj[int | UiResult]:
    ///     """FIDO confirmation.
    ///
    ///     Returns page index in case of confirmation and CANCELLED otherwise.
    ///     """
    Qstr::MP_QSTR_confirm_fido => obj_fn_kw!(0, new_confirm_fido).as_obj(),

    /// def confirm_firmware_update(
    ///     *,
    ///     description: str,
    ///     fingerprint: str,
    /// ) -> LayoutObj[UiResult]:
    ///     """Ask whether to update firmware, optionally show fingerprint."""
    Qstr::MP_QSTR_confirm_firmware_update => obj_fn_kw!(0, new_confirm_firmware_update).as_obj(),

    /// def confirm_homescreen(
    ///     *,
    ///     title: str,
    ///     image: AnyBytes,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm homescreen."""
    Qstr::MP_QSTR_confirm_homescreen => obj_fn_kw!(0, new_confirm_homescreen).as_obj(),

    /// def confirm_modify_fee(
    ///     *,
    ///     title: str,
    ///     sign: int,
    ///     user_fee_change: str,
    ///     total_fee_new: str,
    ///     fee_rate_amount: str | None,
    /// ) -> LayoutObj[UiResult]:
    ///     """Decrease or increase transaction fee."""
    Qstr::MP_QSTR_confirm_modify_fee => obj_fn_kw!(0, new_confirm_modify_fee).as_obj(),

    /// def confirm_modify_output(
    ///     *,
    ///     sign: int,
    ///     amount_change: str,
    ///     amount_new: str,
    /// ) -> LayoutObj[UiResult]:
    ///     """Decrease or increase output amount."""
    Qstr::MP_QSTR_confirm_modify_output => obj_fn_kw!(0, new_confirm_modify_output).as_obj(),

    /// def confirm_more(
    ///     *,
    ///     title: str,
    ///     button: str,
    ///     button_style_confirm: bool = False,
    ///     hold: bool = False,
    ///     items: Iterable[tuple[StrOrBytes, bool]],
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm long content with the possibility to go back from any page.
    ///     Meant to be used with confirm_with_info on UI Bolt and Caesar."""
    Qstr::MP_QSTR_confirm_more => obj_fn_kw!(0, new_confirm_more).as_obj(),

    /// def confirm_properties(
    ///     *,
    ///     title: str,
    ///     subtitle: str | None = None,
    ///     items: Sequence[PropertyType],
    ///     hold: bool = False,
    ///     verb: str | None = None,
    ///     external_menu: bool = False,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm list of key-value pairs. The third component in the tuple should be True if
    ///     the value is to be rendered as binary with monospace font, False otherwise."""
    Qstr::MP_QSTR_confirm_properties => obj_fn_kw!(0, new_confirm_properties).as_obj(),

    /// def confirm_reset_device(recovery: bool) -> LayoutObj[UiResult]:
    ///     """Confirm TOS before creating wallet creation or wallet recovery."""
    Qstr::MP_QSTR_confirm_reset_device => obj_fn_kw!(0, new_confirm_reset_device).as_obj(),

    /// def confirm_summary(
    ///     *,
    ///     amount: str | None,
    ///     amount_label: str | None,
    ///     fee: str,
    ///     fee_label: str,
    ///     title: str | None = None,
    ///     account_items: Sequence[PropertyType] | None = None,
    ///     account_title: str | None = None,
    ///     extra_items: Sequence[PropertyType] | None = None,
    ///     extra_title: str | None = None,
    ///     verb_cancel: str | None = None,
    ///     back_button: bool = False,
    ///     external_menu: bool = False,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm summary of a transaction."""
    Qstr::MP_QSTR_confirm_summary => obj_fn_kw!(0, new_confirm_summary).as_obj(),

    /// def confirm_with_info(
    ///     *,
    ///     title: str,
    ///     subtitle: str | None = None,
    ///     items: Iterable[tuple[StrOrBytes, bool]],
    ///     verb: str,
    ///     verb_info: str,
    ///     verb_cancel: str | None = None,
    ///     external_menu: bool = False,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm given items but with third button. Always single page
    ///     without scrolling. In Delizia, the button is placed in
    ///     context menu."""
    Qstr::MP_QSTR_confirm_with_info => obj_fn_kw!(0, new_confirm_with_info).as_obj(),

    /// def continue_recovery_homepage(
    ///     *,
    ///     text: str,
    ///     subtext: str | None,
    ///     button: str | None,
    ///     recovery_type: RecoveryType,
    ///     show_instructions: bool = False,  # unused on bolt
    ///     remaining_shares: Iterable[tuple[str, str]] | None = None,
    /// ) -> LayoutObj[UiResult]:
    ///     """Device recovery homescreen."""
    Qstr::MP_QSTR_continue_recovery_homepage => obj_fn_kw!(0, new_continue_recovery_homepage).as_obj(),

    /// def flow_confirm_output(
    ///     *,
    ///     title: str | None,
    ///     subtitle: str | None,
    ///     message: str,
    ///     description: str | None,
    ///     extra: str | None,
    ///     chunkify: bool,
    ///     text_mono: bool,
    ///     account_title: str,
    ///     account: str | None,
    ///     account_path: str | None,
    ///     br_code: ButtonRequestType,
    ///     br_name: str,
    ///     address_item: PropertyType | None,
    ///     extra_item: PropertyType | None,
    ///     summary_items: Sequence[PropertyType] | None = None,
    ///     fee_items: Sequence[PropertyType] | None = None,
    ///     summary_title: str | None = None,
    ///     summary_br_code: ButtonRequestType | None = None,
    ///     summary_br_name: str | None = None,
    ///     cancel_text: str | None = None,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm the recipient, (optionally) confirm the amount and (optionally) confirm the summary and present a Hold to Sign page."""
    Qstr::MP_QSTR_flow_confirm_output => obj_fn_kw!(0, new_flow_confirm_output).as_obj(),

    /// def flow_confirm_set_new_code(
    ///     *,
    ///     is_wipe_code: bool,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm new PIN/wipe code setup with an option to cancel action."""
    Qstr::MP_QSTR_flow_confirm_set_new_code => obj_fn_kw!(0, new_flow_confirm_set_new_code).as_obj(),

    /// def flow_get_address(
    ///     *,
    ///     address: str,
    ///     title: str,
    ///     subtitle: str | None,
    ///     description: str | None,
    ///     hint: str | None,
    ///     chunkify: bool,
    ///     address_qr: str,
    ///     case_sensitive: bool,
    ///     account: str | None,
    ///     path: str | None,
    ///     xpubs: Sequence[tuple[str, str]],
    ///     br_code: ButtonRequestType,
    ///     br_name: str,
    /// ) -> LayoutObj[UiResult]:
    ///     """Get address / receive funds."""
    Qstr::MP_QSTR_flow_get_address => obj_fn_kw!(0, new_flow_get_address).as_obj(),

    /// def flow_get_pubkey(
    ///     *,
    ///     pubkey: str,
    ///     title: str,
    ///     subtitle: str | None,
    ///     description: str | None,
    ///     hint: str | None,
    ///     chunkify: bool,
    ///     pubkey_qr: str,
    ///     case_sensitive: bool,
    ///     account: str | None,
    ///     path: str | None,
    ///     br_code: ButtonRequestType,
    ///     br_name: str,
    /// ) -> LayoutObj[UiResult]:
    ///     """Get public key."""
    Qstr::MP_QSTR_flow_get_pubkey => obj_fn_kw!(0, new_flow_get_pubkey).as_obj(),

    /// def multiple_pages_texts(
    ///     *,
    ///     title: str,
    ///     verb: str,
    ///     items: Sequence[str],
    /// ) -> LayoutObj[UiResult]:
    ///     """Show multiple texts, each on its own page. TR specific."""
    Qstr::MP_QSTR_multiple_pages_texts => obj_fn_kw!(0, new_multiple_pages_texts).as_obj(),

    /// def prompt_backup() -> LayoutObj[UiResult]:
    ///     """Strongly recommend user to do a backup."""
    Qstr::MP_QSTR_prompt_backup => obj_fn_0!(new_prompt_backup).as_obj(),

    /// def request_bip39(
    ///     *,
    ///     prompt: str,
    ///     prefill_word: str,
    ///     can_go_back: bool,
    /// ) -> LayoutObj[str]:
    ///     """BIP39 word input keyboard."""
    Qstr::MP_QSTR_request_bip39 => obj_fn_kw!(0, new_request_bip39).as_obj(),

    /// def request_slip39(
    ///     *,
    ///     prompt: str,
    ///     prefill_word: str,
    ///     can_go_back: bool,
    /// ) -> LayoutObj[str]:
    ///     """SLIP39 word input keyboard."""
    Qstr::MP_QSTR_request_slip39 => obj_fn_kw!(0, new_request_slip39).as_obj(),

    /// def request_number(
    ///     *,
    ///     title: str,
    ///     count: int,
    ///     min_count: int,
    ///     max_count: int,
    ///     description: str | None = None,
    ///     more_info_callback: Callable[[int], str] | None = None,
    /// ) -> LayoutObj[tuple[UiResult, int]]:
    ///     """Number input with + and - buttons, optional static description and optional dynamic
    ///     description."""
    Qstr::MP_QSTR_request_number => obj_fn_kw!(0, new_request_number).as_obj(),

    /// def request_duration(
    ///     *,
    ///     title: str,
    ///     duration_ms: int,
    ///     min_ms: int,
    ///     max_ms: int,
    ///     description: str | None = None,
    /// ) -> LayoutObj[tuple[UiResult, int]]:
    ///     """Duration input with + and - buttons, optional static description. """
    Qstr::MP_QSTR_request_duration => obj_fn_kw!(0, new_request_duration).as_obj(),

    /// def request_pin(
    ///     *,
    ///     prompt: str,
    ///     attempts: str,
    ///     allow_cancel: bool = True,
    ///     wrong_pin: bool = False,
    ///     last_attempt: bool = False,
    /// ) -> LayoutObj[str | UiResult]:
    ///     """Request pin on device."""
    Qstr::MP_QSTR_request_pin => obj_fn_kw!(0, new_request_pin).as_obj(),

    /// def request_passphrase(
    ///     *,
    ///     prompt: str,
    ///     prompt_empty: str,
    ///     max_len: int,
    /// ) -> LayoutObj[str | UiResult]:
    ///     """Passphrase input keyboard."""
    Qstr::MP_QSTR_request_passphrase => obj_fn_kw!(0, new_request_passphrase).as_obj(),

    /// def request_string(
    ///     *,
    ///     prompt: str,
    ///     max_len: int,
    ///     allow_empty: bool,
    ///     prefill: str | None,
    /// ) -> LayoutObj[str | UiResult]:
    ///     """Label input keyboard."""
    Qstr::MP_QSTR_request_string => obj_fn_kw!(0, new_request_string).as_obj(),

    /// def select_menu(
    ///     *,
    ///     items: Iterable[str],
    ///     current: int,
    ///     cancel: str | None = None
    /// ) -> LayoutObj[int]:
    ///     """Select an item from a menu. Returns index in range `0..len(items)`."""
    Qstr::MP_QSTR_select_menu => obj_fn_kw!(0, new_select_menu).as_obj(),

    /// def select_word(
    ///     *,
    ///     title: str,
    ///     description: str,
    ///     words: Iterable[str],
    /// ) -> LayoutObj[int]:
    ///     """Select mnemonic word from three possibilities - seed check after backup. The
    ///     iterable must be of exact size. Returns index in range `0..3`."""
    Qstr::MP_QSTR_select_word => obj_fn_kw!(0, new_select_word).as_obj(),

    /// def select_word_count(
    ///     *,
    ///     recovery_type: RecoveryType,
    /// ) -> LayoutObj[int | str | UiResult]:  # TR returns str
    ///     """Select a mnemonic word count from the options: 12, 18, 20, 24, or 33.
    ///     For unlocking a repeated backup, select between 20 and 33."""
    Qstr::MP_QSTR_select_word_count => obj_fn_kw!(0, new_select_word_count).as_obj(),

    /// def set_brightness(*, current: int | None = None) -> LayoutObj[UiResult]:
    ///     """Show the brightness configuration dialog."""
    Qstr::MP_QSTR_set_brightness => obj_fn_kw!(0, new_set_brightness).as_obj(),

    /// def show_address_details(
    ///     *,
    ///     qr_title: str,
    ///     address: str,
    ///     case_sensitive: bool,
    ///     details_title: str,
    ///     account: str | None,
    ///     path: str | None,
    ///     xpubs: Sequence[tuple[str, str]],
    /// ) -> LayoutObj[UiResult]:
    ///     """Show address details - QR code, account, path, cosigner xpubs."""
    Qstr::MP_QSTR_show_address_details => obj_fn_kw!(0, new_show_address_details).as_obj(),

    /// def show_checklist(
    ///     *,
    ///     title: str,
    ///     items: Iterable[str],
    ///     active: int,
    ///     button: str,
    /// ) -> LayoutObj[UiResult]:
    ///     """Checklist of backup steps. Active index is highlighted, previous items have check
    ///     mark next to them. Limited to 3 items."""
    Qstr::MP_QSTR_show_checklist => obj_fn_kw!(0, new_show_checklist).as_obj(),

    /// def show_danger(
    ///     *,
    ///     title: str,
    ///     description: str,
    ///     value: str = "",
    ///     menu_title: str | None = None,
    ///     verb_cancel: str | None = None,
    /// ) -> LayoutObj[UiResult]:
    ///     """Warning modal that makes it easier to cancel than to continue."""
    Qstr::MP_QSTR_show_danger => obj_fn_kw!(0, new_show_danger).as_obj(),

    /// def show_error(
    ///     *,
    ///     title: str,
    ///     button: str,
    ///     description: str = "",
    ///     allow_cancel: bool = True,
    ///     time_ms: int = 0,
    /// ) -> LayoutObj[UiResult]:
    ///     """Error modal. No buttons shown when `button` is empty string."""
    Qstr::MP_QSTR_show_error => obj_fn_kw!(0, new_show_error).as_obj(),

    /// def show_group_share_success(
    ///     *,
    ///     lines: Iterable[str],
    /// ) -> LayoutObj[UiResult]:
    ///     """Shown after successfully finishing a group."""
    Qstr::MP_QSTR_show_group_share_success => obj_fn_kw!(0, new_show_group_share_success).as_obj(),

    /// def show_homescreen(
    ///     *,
    ///     label: str,
    ///     notification: str | None,
    ///     notification_level: int = 0,
    ///     lockable: bool,
    ///     skip_first_paint: bool,
    /// ) -> LayoutObj[UiResult]:
    ///     """Idle homescreen."""
    Qstr::MP_QSTR_show_homescreen => obj_fn_kw!(0, new_show_homescreen).as_obj(),

    /// def show_device_menu(
    ///     *,
    ///     init_submenu_idx: int | None,
    ///     backup_failed: bool,
    ///     backup_needed: bool,
    ///     ble_enabled: bool,
    ///     paired_devices: Iterable[tuple[str, tuple[str, str] | None]],
    ///     connected_idx: int | None,
    ///     pin_enabled: bool | None,
    ///     auto_lock: tuple[str, str] | None,
    ///     wipe_code_enabled: bool | None,
    ///     backup_check_allowed: bool,
    ///     device_name: str | None,
    ///     brightness: str | None,
    ///     haptics_enabled: bool | None,
    ///     led_enabled: bool | None,
    ///     about_items: Sequence[tuple[str | None, StrOrBytes | None, bool | None]],
    /// ) -> LayoutObj[UiResult | tuple[int, int | None, int]]:
    ///     """Show the device menu. Result is either CANCELLED or a tuple (action, action_arg, parent_menu_id)."""
    Qstr::MP_QSTR_show_device_menu => obj_fn_kw!(0, new_show_device_menu).as_obj(),

    /// def show_pairing_device_name(
    ///     *,
    ///     description: str,
    ///     device_name: str,
    /// ) -> LayoutObj[UiResult]:
    ///     """Pairing device: first screen (device name).
    ///     Returns if BLEEvent::PairingRequest is received."""
    Qstr::MP_QSTR_show_pairing_device_name => obj_fn_kw!(0, new_show_pairing_device_name).as_obj(),

    /// def show_ble_pairing_code(
    ///     *,
    ///     title: str,
    ///     description: str,
    ///     code: str,
    /// ) -> LayoutObj[UiResult]:
    ///     """BLE pairing: second screen (pairing code).
    ///     Returns on BLEEvent::{PairingCanceled, Disconnected}."""
    Qstr::MP_QSTR_show_ble_pairing_code => obj_fn_kw!(0, new_show_ble_pairing_code).as_obj(),

    /// def wait_ble_host_confirmation(
    ///     *,
    /// ) -> LayoutObj[UiResult]:
    ///     """Pairing device: third screen (waiting for host confirmation).
    ///     Returns on BLEEvent::{PairingCanceled, Disconnected}."""
    Qstr::MP_QSTR_wait_ble_host_confirmation => obj_fn_kw!(0, new_wait_ble_host_confirmation).as_obj(),

    /// def confirm_thp_pairing(
    ///     *,
    ///     title: str,
    ///     description: str,
    ///     args: Iterable[str],
    /// ) -> LayoutObj[UiResult]:
    ///     """THP pairing: first screen (host and app names)."""
    Qstr::MP_QSTR_confirm_thp_pairing => obj_fn_kw!(0, new_confirm_thp_pairing).as_obj(),

    /// def show_thp_pairing_code(
    ///     *,
    ///     title: str,
    ///     description: str,
    ///     code: str,
    /// ) -> LayoutObj[UiResult]:
    ///     """THP pairing: second screen (pairing code)."""
    Qstr::MP_QSTR_show_thp_pairing_code => obj_fn_kw!(0, new_show_thp_pairing_code).as_obj(),

    /// def show_info(
    ///     *,
    ///     title: str,
    ///     description: str = "",
    ///     button: str = "",
    ///     time_ms: int = 0,
    /// ) -> LayoutObj[UiResult]:
    ///     """Info screen."""
    Qstr::MP_QSTR_show_info => obj_fn_kw!(0, new_show_info).as_obj(),

    /// def show_info_with_cancel(
    ///     *,
    ///     title: str,
    ///     items: Sequence[PropertyType],
    ///     horizontal: bool = False,
    ///     chunkify: bool = False,
    /// ) -> LayoutObj[UiResult]:
    ///     """Show metadata for outgoing transaction."""
    Qstr::MP_QSTR_show_info_with_cancel => obj_fn_kw!(0, new_show_info_with_cancel).as_obj(),

    /// def show_lockscreen(
    ///     *,
    ///     label: str | None,
    ///     bootscreen: bool,
    ///     skip_first_paint: bool,
    ///     coinjoin_authorized: bool = False,
    /// ) -> LayoutObj[UiResult]:
    ///     """Homescreen for locked device."""
    Qstr::MP_QSTR_show_lockscreen => obj_fn_kw!(0, new_show_lockscreen).as_obj(),

    /// def show_mismatch(*, title: str) -> LayoutObj[UiResult]:
    ///     """Warning of receiving address mismatch."""
    Qstr::MP_QSTR_show_mismatch => obj_fn_kw!(0, new_show_mismatch).as_obj(),

    /// def show_progress(
    ///     *,
    ///     description: str,
    ///     indeterminate: bool = False,
    ///     title: str | None = None,
    ///     danger: bool = False,
    /// ) -> LayoutObj[UiResult]:
    ///     """Show progress loader. Please note that the number of lines reserved on screen for
    ///     description is determined at construction time. If you want multiline descriptions
    ///     make sure the initial description has at least that amount of lines."""
    Qstr::MP_QSTR_show_progress => obj_fn_kw!(0, new_show_progress).as_obj(),

    /// def show_progress_coinjoin(
    ///     *,
    ///     title: str,
    ///     indeterminate: bool = False,
    ///     time_ms: int = 0,
    ///     skip_first_paint: bool = False,
    /// ) -> LayoutObj[UiResult]:
    ///     """Show progress loader for coinjoin. Returns CANCELLED after a specified time when
    ///     time_ms timeout is passed."""
    Qstr::MP_QSTR_show_progress_coinjoin => obj_fn_kw!(0, new_show_progress_coinjoin).as_obj(),

    /// def show_properties(
    ///     *,
    ///     title: str,
    ///     value: Sequence[PropertyType] | str,
    ///     subtitle: str | None = None,
    /// ) -> LayoutObj[None]:
    ///     """Show a list of key-value pairs, or a monospace string."""
    Qstr::MP_QSTR_show_properties => obj_fn_kw!(0, new_show_properties).as_obj(),

    /// def show_remaining_shares(
    ///     *,
    ///     pages: Iterable[tuple[str, str]],
    /// ) -> LayoutObj[UiResult]:
    ///     """Shows SLIP39 state after info button is pressed on `confirm_recovery`."""
    Qstr::MP_QSTR_show_remaining_shares => obj_fn_kw!(0, new_show_remaining_shares).as_obj(),

    /// def show_share_words(
    ///     *,
    ///     words: Iterable[str],
    ///     title: str | None = None,
    /// ) -> LayoutObj[UiResult]:
    ///     """Show mnemonic for backup."""
    Qstr::MP_QSTR_show_share_words => obj_fn_kw!(0, new_show_share_words).as_obj(),

    /// def show_share_words_extended(
    ///     *,
    ///     words: Iterable[str],
    ///     subtitle: str | None,
    ///     instructions: Iterable[str],
    ///     instructions_verb: str | None,
    ///     text_footer: str | None,
    ///     text_confirm: str,
    ///     text_check: str,
    /// ) -> LayoutObj[UiResult]:
    ///     """Show mnemonic for wallet backup preceded by an instruction screen and followed by a
    ///     confirmation screen."""
    Qstr::MP_QSTR_show_share_words_extended => obj_fn_kw!(0, new_show_share_words_extended).as_obj(),

    /// def show_simple(
    ///     *,
    ///     text: str,
    ///     title: str | None = None,
    ///     button: str | None = None,
    /// ) -> LayoutObj[UiResult]:
    ///     """Simple dialog with text. TT: optional button."""
    Qstr::MP_QSTR_show_simple => obj_fn_kw!(0, new_show_simple).as_obj(),

    /// def show_success(
    ///     *,
    ///     title: str,
    ///     button: str,
    ///     description: str = "",
    ///     allow_cancel: bool = False,
    ///     time_ms: int = 0,
    /// ) -> LayoutObj[UiResult]:
    ///     """Success modal. No buttons shown when `button` is empty string."""
    Qstr::MP_QSTR_show_success => obj_fn_kw!(0, new_show_success).as_obj(),

    /// def show_wait_text(message: str, /) -> LayoutObj[None]:
    ///     """Show single-line text in the middle of the screen."""
    Qstr::MP_QSTR_show_wait_text => obj_fn_1!(new_show_wait_text).as_obj(),

    /// def show_warning(
    ///     *,
    ///     title: str,
    ///     button: str,
    ///     value: str = "",
    ///     description: str = "",
    ///     allow_cancel: bool = True,
    ///     danger: bool = False,  # unused on bolt
    /// ) -> LayoutObj[UiResult]:
    ///     """Warning modal. Bolt: No buttons shown when `button` is empty string. Caesar: middle button and centered text."""
    Qstr::MP_QSTR_show_warning => obj_fn_kw!(0, new_show_warning).as_obj(),

    /// def tutorial() -> LayoutObj[UiResult]:
    ///     """Show user how to interact with the device."""
    Qstr::MP_QSTR_tutorial => obj_fn_kw!(0, new_tutorial).as_obj(),

    /// class BacklightLevels:
    ///     """Backlight levels. Values dynamically update based on user settings."""
    ///     MAX: ClassVar[int]
    ///     NORMAL: ClassVar[int]
    ///     LOW: ClassVar[int]
    ///     DIM: ClassVar[int]
    ///     NONE: ClassVar[int]
    ///
    /// mock:global
    Qstr::MP_QSTR_BacklightLevels => BACKLIGHT_LEVELS_OBJ.as_obj(),

    /// class AttachType:
    ///     INITIAL: ClassVar[int]
    ///     RESUME: ClassVar[int]
    ///     SWIPE_UP: ClassVar[int]
    ///     SWIPE_DOWN: ClassVar[int]
    ///     SWIPE_LEFT: ClassVar[int]
    ///     SWIPE_RIGHT: ClassVar[int]
    Qstr::MP_QSTR_AttachType => ATTACH_TYPE_OBJ.as_obj(),

    /// class LayoutState:
    ///     """Layout state."""
    ///     INITIAL: "ClassVar[LayoutState]"
    ///     ATTACHED: "ClassVar[LayoutState]"
    ///     TRANSITIONING: "ClassVar[LayoutState]"
    ///     DONE: "ClassVar[LayoutState]"
    Qstr::MP_QSTR_LayoutState => LAYOUT_STATE.as_obj(),

    /// class DeviceMenuResult:
    ///     """Result of a device menu operation."""
    ///     ReviewFailedBackup: ClassVar[int]
    ///     DisconnectDevice: ClassVar[int]
    ///     PairDevice: ClassVar[int]
    ///     UnpairDevice: ClassVar[int]
    ///     UnpairAllDevices: ClassVar[int]
    ///     ToggleBluetooth: ClassVar[int]
    ///     SetOrChangePin: ClassVar[int]
    ///     RemovePin: ClassVar[int]
    ///     SetAutoLockBattery: ClassVar[int]
    ///     SetAutoLockUSB: ClassVar[int]
    ///     SetOrChangeWipeCode: ClassVar[int]
    ///     RemoveWipeCode: ClassVar[int]
    ///     CheckBackup: ClassVar[int]
    ///     SetDeviceName: ClassVar[int]
    ///     SetBrightness: ClassVar[int]
    ///     ToggleHaptics: ClassVar[int]
    ///     ToggleLed: ClassVar[int]
    ///     WipeDevice: ClassVar[int]
    ///     Reboot: ClassVar[int]
    ///     RebootToBootloader: ClassVar[int]
    ///     TurnOff: ClassVar[int]
    ///     RefreshMenu: ClassVar[int]
    Qstr::MP_QSTR_DeviceMenuResult => DEVICE_MENU_RESULT.as_obj(),
};
