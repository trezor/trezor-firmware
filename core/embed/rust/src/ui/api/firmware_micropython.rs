use crate::{
    io::BinaryData,
    micropython::{
        gc::Gc,
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
            obj::{ComponentMsgObj, LayoutObj, ATTACH_TYPE_OBJ},
            result::{CANCELLED, CONFIRMED, INFO},
            util::{upy_disable_animation, RecoveryType},
        },
        ui_firmware::{
            FirmwareUI, MAX_CHECKLIST_ITEMS, MAX_GROUP_SHARE_LINES, MAX_WORD_QUIZ_ITEMS,
        },
        ModelUI,
    },
};
use heapless::Vec;

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

extern "C" fn new_confirm_blob(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let data: Obj = kwargs.get(Qstr::MP_QSTR_data)?;
        let description: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_description)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let text_mono: bool = kwargs.get_or(Qstr::MP_QSTR_text_mono, true)?;
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
        let verb_info: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_verb_info)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let info: bool = kwargs.get_or(Qstr::MP_QSTR_info, false)?;
        let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;
        let chunkify: bool = kwargs.get_or(Qstr::MP_QSTR_chunkify, false)?;
        let page_counter: bool = kwargs.get_or(Qstr::MP_QSTR_page_counter, false)?;
        let prompt_screen: bool = kwargs.get_or(Qstr::MP_QSTR_prompt_screen, false)?;
        let cancel: bool = kwargs.get_or(Qstr::MP_QSTR_cancel, false)?;

        let layout_obj = ModelUI::confirm_blob(
            title,
            data,
            description,
            text_mono,
            extra,
            subtitle,
            verb,
            verb_cancel,
            verb_info,
            info,
            hold,
            chunkify,
            page_counter,
            prompt_screen,
            cancel,
        )?;
        Ok(layout_obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_blob_intro(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let data: Obj = kwargs.get(Qstr::MP_QSTR_data)?;
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
        let chunkify: bool = kwargs.get_or(Qstr::MP_QSTR_chunkify, false)?;

        let layout_obj =
            ModelUI::confirm_blob_intro(title, data, subtitle, verb, verb_cancel, chunkify)?;
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
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;

        let layout = ModelUI::confirm_more(title, button, button_style_confirm, items)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_properties(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;
        let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;

        let layout = ModelUI::confirm_properties(title, items, hold)?;
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
        let amount: TString = kwargs.get(Qstr::MP_QSTR_amount)?.try_into()?;
        let amount_label: TString = kwargs.get(Qstr::MP_QSTR_amount_label)?.try_into()?;
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

        let layout = ModelUI::confirm_summary(
            amount,
            amount_label,
            fee,
            fee_label,
            title,
            account_items,
            extra_items,
            extra_title,
            verb_cancel,
        )?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_value(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let subtitle: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_subtitle)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let description: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_description)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let value: Obj = kwargs.get(Qstr::MP_QSTR_value)?;
        let info_button: bool = kwargs.get_or(Qstr::MP_QSTR_info_button, false)?;
        let verb: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_verb)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let verb_info: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_verb_info)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let verb_cancel: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_verb_cancel)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;
        let chunkify: bool = kwargs.get_or(Qstr::MP_QSTR_chunkify, false)?;
        let text_mono: bool = kwargs.get_or(Qstr::MP_QSTR_text_mono, true)?;

        let layout_obj = ModelUI::confirm_value(
            title,
            value,
            description,
            subtitle,
            verb,
            verb_info,
            verb_cancel,
            info_button,
            hold,
            chunkify,
            text_mono,
        )?;
        Ok(layout_obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_with_info(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let button: TString = kwargs.get(Qstr::MP_QSTR_button)?.try_into()?;
        let info_button: TString = kwargs.get(Qstr::MP_QSTR_info_button)?.try_into()?;
        let verb_cancel: Option<TString<'static>> = kwargs
            .get(Qstr::MP_QSTR_verb_cancel)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;

        let layout = ModelUI::confirm_with_info(title, button, info_button, verb_cancel, items)?;
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
        let message: Obj = kwargs.get(Qstr::MP_QSTR_message)?;
        let amount: Option<Obj> = kwargs.get(Qstr::MP_QSTR_amount)?.try_into_option()?;
        let chunkify: bool = kwargs.get_or(Qstr::MP_QSTR_chunkify, false)?;
        let text_mono: bool = kwargs.get_or(Qstr::MP_QSTR_text_mono, true)?;
        let account: Option<TString> = kwargs.get(Qstr::MP_QSTR_account)?.try_into_option()?;
        let account_path: Option<TString> =
            kwargs.get(Qstr::MP_QSTR_account_path)?.try_into_option()?;
        let br_code: u16 = kwargs.get(Qstr::MP_QSTR_br_code)?.try_into()?;
        let br_name: TString = kwargs.get(Qstr::MP_QSTR_br_name)?.try_into()?;

        let address: Option<Obj> = kwargs.get(Qstr::MP_QSTR_address)?.try_into_option()?;
        let address_title: Option<TString> =
            kwargs.get(Qstr::MP_QSTR_address_title)?.try_into_option()?;
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
            message,
            amount,
            chunkify,
            text_mono,
            account,
            account_path,
            br_code,
            br_name,
            address,
            address_title,
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

extern "C" fn new_flow_confirm_set_new_pin(
    n_args: usize,
    args: *const Obj,
    kwargs: *mut Map,
) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: TString = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;

        let layout = ModelUI::flow_confirm_set_new_pin(title, description)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_flow_get_address(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: Option<TString> =
            kwargs.get(Qstr::MP_QSTR_description)?.try_into_option()?;
        let extra: Option<TString> = kwargs.get(Qstr::MP_QSTR_extra)?.try_into_option()?;
        let address: Obj = kwargs.get(Qstr::MP_QSTR_address)?;
        let chunkify: bool = kwargs.get_or(Qstr::MP_QSTR_chunkify, false)?;
        let address_qr: TString = kwargs.get(Qstr::MP_QSTR_address_qr)?.try_into()?;
        let case_sensitive: bool = kwargs.get(Qstr::MP_QSTR_case_sensitive)?.try_into()?;
        let account: Option<TString> = kwargs.get(Qstr::MP_QSTR_account)?.try_into_option()?;
        let path: Option<TString> = kwargs.get(Qstr::MP_QSTR_path)?.try_into_option()?;
        let xpubs: Obj = kwargs.get(Qstr::MP_QSTR_xpubs)?;
        let title_success: TString = kwargs.get(Qstr::MP_QSTR_title_success)?.try_into()?;
        let br_code: u16 = kwargs.get(Qstr::MP_QSTR_br_code)?.try_into()?;
        let br_name: TString = kwargs.get(Qstr::MP_QSTR_br_name)?.try_into()?;

        let layout = ModelUI::flow_get_address(
            address,
            title,
            description,
            extra,
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

extern "C" fn new_request_pin(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let prompt: TString = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let subprompt: TString = kwargs.get(Qstr::MP_QSTR_subprompt)?.try_into()?;
        let allow_cancel: bool = kwargs.get_or(Qstr::MP_QSTR_allow_cancel, true)?;
        let warning: bool = kwargs.get_or(Qstr::MP_QSTR_wrong_pin, false)?;

        let layout = ModelUI::request_pin(prompt, subprompt, allow_cancel, warning)?;
        Ok(LayoutObj::new_root(layout)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_passphrase(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let prompt: TString = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let max_len: u32 = kwargs.get(Qstr::MP_QSTR_max_len)?.try_into()?;

        let layout = ModelUI::request_passphrase(prompt, max_len)?;
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
        let verb_cancel: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_verb_cancel)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;

        let layout = ModelUI::show_danger(title, description, value, verb_cancel)?;
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
        let label: TString<'static> = kwargs
            .get(Qstr::MP_QSTR_label)?
            .try_into_option()?
            .unwrap_or_else(|| model::FULL_NAME.into());
        let notification: Option<TString<'static>> =
            kwargs.get(Qstr::MP_QSTR_notification)?.try_into_option()?;
        let notification_level: u8 = kwargs.get_or(Qstr::MP_QSTR_notification_level, 0)?;
        let hold: bool = kwargs.get(Qstr::MP_QSTR_hold)?.try_into()?;
        let skip_first_paint: bool = kwargs.get(Qstr::MP_QSTR_skip_first_paint)?.try_into()?;

        let layout = ModelUI::show_homescreen(label, hold, notification, notification_level)?;
        let layout_obj = LayoutObj::new_root(layout)?;
        if skip_first_paint {
            layout_obj.skip_first_paint();
        }
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

        let layout = ModelUI::show_progress(description, indeterminate, title)?;
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

extern "C" fn new_show_share_words_mercury(
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
        let text_footer: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_text_footer)
            .and_then(Obj::try_into_option)
            .unwrap_or(None);
        let text_confirm: TString = kwargs.get(Qstr::MP_QSTR_text_confirm)?.try_into()?;

        let words: Vec<TString, 33> = util::iter_into_vec(words)?;

        let layout = ModelUI::show_share_words_mercury(
            words,
            subtitle,
            instructions,
            text_footer,
            text_confirm,
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

#[no_mangle]
pub static mp_module_trezorui_api: Module = obj_module! {
    /// from trezor import utils
    ///
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
    ///     def button_request(self) -> tuple[int, str] | None:
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

    /// CANCELLED: UiResult
    Qstr::MP_QSTR_CANCELLED => CANCELLED.as_obj(),

    /// INFO: UiResult
    Qstr::MP_QSTR_INFO => INFO.as_obj(),

    /// def check_homescreen_format(data: bytes) -> bool:
    ///     """Check homescreen format and dimensions."""
    Qstr::MP_QSTR_check_homescreen_format => obj_fn_1!(upy_check_homescreen_format).as_obj(),

    /// def disable_animation(disable: bool) -> None:
    ///     """Disable animations, debug builds only."""
    Qstr::MP_QSTR_disable_animation => obj_fn_1!(upy_disable_animation).as_obj(),

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
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm action."""
    Qstr::MP_QSTR_confirm_action => obj_fn_kw!(0, new_confirm_action).as_obj(),

    /// def confirm_address(
    ///     *,
    ///     title: str,
    ///     address: str | bytes,
    ///     address_label: str | None = None,
    ///     verb: str | None = None,
    ///     info_button: bool = False,
    ///     chunkify: bool = False,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm address."""
    Qstr::MP_QSTR_confirm_address => obj_fn_kw!(0, new_confirm_address).as_obj(),

    /// def confirm_blob(
    ///     *,
    ///     title: str,
    ///     data: str | bytes,
    ///     description: str | None,
    ///     text_mono: bool = True,
    ///     extra: str | None = None,
    ///     subtitle: str | None = None,
    ///     verb: str | None = None,
    ///     verb_cancel: str | None = None,
    ///     verb_info: str | None = None,
    ///     info: bool = True,
    ///     hold: bool = False,
    ///     chunkify: bool = False,
    ///     page_counter: bool = False,
    ///     prompt_screen: bool = False,
    ///     cancel: bool = False,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm byte sequence data."""
    Qstr::MP_QSTR_confirm_blob => obj_fn_kw!(0, new_confirm_blob).as_obj(),

    /// def confirm_blob_intro(
    ///     *,
    ///     title: str,
    ///     data: str | bytes,
    ///     subtitle: str | None = None,
    ///     verb: str | None = None,
    ///     verb_cancel: str | None = None,
    ///     chunkify: bool = False,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm byte sequence data by showing only the first page of the data
    ///     and instructing the user to access the menu in order to view all the data,
    ///     which can then be confirmed using confirm_blob."""
    Qstr::MP_QSTR_confirm_blob_intro => obj_fn_kw!(0, new_confirm_blob_intro).as_obj(),

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
    ///     accounts: list[str | None],
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
    ///     image: bytes,
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
    ///     items: Iterable[tuple[int, str | bytes]],
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm long content with the possibility to go back from any page.
    ///     Meant to be used with confirm_with_info on model TT and TR."""
    Qstr::MP_QSTR_confirm_more => obj_fn_kw!(0, new_confirm_more).as_obj(),

    /// def confirm_properties(
    ///     *,
    ///     title: str,
    ///     items: list[tuple[str | None, str | bytes | None, bool]],
    ///     hold: bool = False,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm list of key-value pairs. The third component in the tuple should be True if
    ///     the value is to be rendered as binary with monospace font, False otherwise."""
    Qstr::MP_QSTR_confirm_properties => obj_fn_kw!(0, new_confirm_properties).as_obj(),

    /// def confirm_reset_device(recovery: bool) -> LayoutObj[UiResult]:
    ///     """Confirm TOS before creating wallet creation or wallet recovery."""
    Qstr::MP_QSTR_confirm_reset_device => obj_fn_kw!(0, new_confirm_reset_device).as_obj(),

    /// def confirm_summary(
    ///     *,
    ///     amount: str,
    ///     amount_label: str,
    ///     fee: str,
    ///     fee_label: str,
    ///     title: str | None = None,
    ///     account_items: Iterable[tuple[str, str]] | None = None,
    ///     extra_items: Iterable[tuple[str, str]] | None = None,
    ///     extra_title: str | None = None,
    ///     verb_cancel: str | None = None,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm summary of a transaction."""
    Qstr::MP_QSTR_confirm_summary => obj_fn_kw!(0, new_confirm_summary).as_obj(),

    /// def confirm_value(
    ///     *,
    ///     title: str,
    ///     value: str,
    ///     description: str | None,
    ///     subtitle: str | None,
    ///     verb: str | None = None,
    ///     verb_info: str | None = None,
    ///     verb_cancel: str | None = None,
    ///     info_button: bool = False,
    ///     hold: bool = False,
    ///     chunkify: bool = False,
    ///     text_mono: bool = True,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm value. Merge of confirm_total and confirm_output."""
    Qstr::MP_QSTR_confirm_value => obj_fn_kw!(0, new_confirm_value).as_obj(),

    /// def confirm_with_info(
    ///     *,
    ///     title: str,
    ///     button: str,
    ///     info_button: str,
    ///     verb_cancel: str | None = None,
    ///     items: Iterable[tuple[int, str | bytes]],
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm given items but with third button. Always single page
    ///     without scrolling. In mercury, the button is placed in
    ///     context menu."""
    Qstr::MP_QSTR_confirm_with_info => obj_fn_kw!(0, new_confirm_with_info).as_obj(),

    /// def continue_recovery_homepage(
    ///     *,
    ///     text: str,
    ///     subtext: str | None,
    ///     button: str | None,
    ///     recovery_type: RecoveryType,
    ///     show_instructions: bool = False,  # unused on TT
    ///     remaining_shares: Iterable[tuple[str, str]] | None = None,
    /// ) -> LayoutObj[UiResult]:
    ///     """Device recovery homescreen."""
    Qstr::MP_QSTR_continue_recovery_homepage => obj_fn_kw!(0, new_continue_recovery_homepage).as_obj(),

    /// def flow_confirm_output(
    ///     *,
    ///     title: str | None,
    ///     subtitle: str | None,
    ///     message: str,
    ///     amount: str | None,
    ///     chunkify: bool,
    ///     text_mono: bool,
    ///     account: str | None,
    ///     account_path: str | None,
    ///     br_code: ButtonRequestType,
    ///     br_name: str,
    ///     address: str | None,
    ///     address_title: str | None,
    ///     summary_items: Iterable[tuple[str, str]] | None = None,
    ///     fee_items: Iterable[tuple[str, str]] | None = None,
    ///     summary_title: str | None = None,
    ///     summary_br_code: ButtonRequestType | None = None,
    ///     summary_br_name: str | None = None,
    ///     cancel_text: str | None = None,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm the recipient, (optionally) confirm the amount and (optionally) confirm the summary and present a Hold to Sign page."""
    Qstr::MP_QSTR_flow_confirm_output => obj_fn_kw!(0, new_flow_confirm_output).as_obj(),

    // TODO: supply more arguments for Wipe code setting (mercury)
    ///
    /// def flow_confirm_set_new_pin(
    ///     *,
    ///     title: str,
    ///     description: str,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm new PIN setup with an option to cancel action."""
    Qstr::MP_QSTR_flow_confirm_set_new_pin => obj_fn_kw!(0, new_flow_confirm_set_new_pin).as_obj(),

    /// def flow_get_address(
    ///     *,
    ///     address: str | bytes,
    ///     title: str,
    ///     description: str | None,
    ///     extra: str | None,
    ///     chunkify: bool,
    ///     address_qr: str,
    ///     case_sensitive: bool,
    ///     account: str | None,
    ///     path: str | None,
    ///     xpubs: list[tuple[str, str]],
    ///     title_success: str,
    ///     br_code: ButtonRequestType,
    ///     br_name: str,
    /// ) -> LayoutObj[UiResult]:
    ///     """Get address / receive funds."""
    Qstr::MP_QSTR_flow_get_address => obj_fn_kw!(0, new_flow_get_address).as_obj(),

    /// def multiple_pages_texts(
    ///     *,
    ///     title: str,
    ///     verb: str,
    ///     items: list[str],
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

    /// def request_pin(
    ///     *,
    ///     prompt: str,
    ///     subprompt: str,
    ///     allow_cancel: bool = True,
    ///     wrong_pin: bool = False,
    /// ) -> LayoutObj[str | UiResult]:
    ///     """Request pin on device."""
    Qstr::MP_QSTR_request_pin => obj_fn_kw!(0, new_request_pin).as_obj(),

    /// def request_passphrase(
    ///     *,
    ///     prompt: str,
    ///     max_len: int,
    /// ) -> LayoutObj[str | UiResult]:
    ///     """Passphrase input keyboard."""
    Qstr::MP_QSTR_request_passphrase => obj_fn_kw!(0, new_request_passphrase).as_obj(),

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
    /// ) -> LayoutObj[int | str]:  # TR returns str
    ///     """Select a mnemonic word count from the options: 12, 18, 20, 24, or 33.
    ///     For unlocking a repeated backup, select from 20 or 33."""
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
    ///     xpubs: list[tuple[str, str]],
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
    ///     label: str | None,
    ///     hold: bool,
    ///     notification: str | None,
    ///     notification_level: int = 0,
    ///     skip_first_paint: bool,
    /// ) -> LayoutObj[UiResult]:
    ///     """Idle homescreen."""
    Qstr::MP_QSTR_show_homescreen => obj_fn_kw!(0, new_show_homescreen).as_obj(),

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
    ///     items: Iterable[tuple[str, str]],
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

    /// def show_share_words_mercury(
    ///     *,
    ///     words: Iterable[str],
    ///     subtitle: str | None,
    ///     instructions: Iterable[str],
    ///     text_footer: str | None,
    ///     text_confirm: str,
    /// ) -> LayoutObj[UiResult]:
    ///     """Show mnemonic for wallet backup preceded by an instruction screen and followed by a
    ///     confirmation screen."""
    Qstr::MP_QSTR_show_share_words_mercury => obj_fn_kw!(0, new_show_share_words_mercury).as_obj(),

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
    ///     allow_cancel: bool = True,
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
    ///     danger: bool = False,  # unused on TT
    /// ) -> LayoutObj[UiResult]:
    ///     """Warning modal. TT: No buttons shown when `button` is empty string. TR: middle button and centered text."""
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

};
