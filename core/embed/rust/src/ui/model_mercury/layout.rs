use core::{cmp::Ordering, convert::TryInto};
use heapless::Vec;

use super::{
    component::{
        AddressDetails, Bip39Input, CoinJoinProgress, Frame, FrameMsg, Homescreen, HomescreenMsg,
        Lockscreen, MnemonicInput, MnemonicKeyboard, MnemonicKeyboardMsg, PinKeyboard,
        PinKeyboardMsg, Progress, PromptScreen, SelectWordCount, SelectWordCountMsg, Slip39Input,
        StatusScreen, SwipeUpScreen, SwipeUpScreenMsg, VerticalMenu, VerticalMenuChoiceMsg,
    },
    flow::{self, confirm_with_info},
    theme,
};
use crate::{
    error::{value_error, Error},
    io::BinaryData,
    micropython::{
        iter::IterBuf,
        macros::{obj_fn_0, obj_fn_1, obj_fn_kw, obj_module},
        map::Map,
        module::Module,
        obj::Obj,
        qstr::Qstr,
        util,
    },
    strutil::TString,
    translations::TR,
    trezorhal::model,
    ui::{
        backlight::BACKLIGHT_LEVELS_OBJ,
        component::{
            base::ComponentExt,
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
            Border, CachedJpeg, Component, FormattedText, Never, Timeout,
        },
        flow::Swipable,
        geometry::{self, Direction},
        layout::{
            base::LAYOUT_STATE,
            obj::{ComponentMsgObj, LayoutObj, ATTACH_TYPE_OBJ},
            result::{CANCELLED, CONFIRMED, INFO},
            util::{upy_disable_animation, ConfirmBlob, PropsList, RecoveryType},
        },
        model_mercury::{
            component::{check_homescreen_format, SwipeContent},
            flow::{
                new_confirm_action_simple,
                util::{ConfirmBlobParams, ShowInfoParams},
                ConfirmActionExtra, ConfirmActionMenuStrings, ConfirmActionStrings,
            },
            theme::ICON_BULLET_CHECKMARK,
        },
    },
};

const CONFIRM_BLOB_INTRO_MARGIN: usize = 24;

impl TryFrom<SelectWordCountMsg> for Obj {
    type Error = Error;

    fn try_from(value: SelectWordCountMsg) -> Result<Self, Self::Error> {
        match value {
            SelectWordCountMsg::Selected(i) => i.try_into(),
        }
    }
}

impl TryFrom<VerticalMenuChoiceMsg> for Obj {
    type Error = Error;

    fn try_from(value: VerticalMenuChoiceMsg) -> Result<Self, Self::Error> {
        match value {
            VerticalMenuChoiceMsg::Selected(i) => i.try_into(),
        }
    }
}

impl ComponentMsgObj for PinKeyboard<'_> {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            PinKeyboardMsg::Confirmed => self.pin().try_into(),
            PinKeyboardMsg::Cancelled => Ok(CANCELLED.as_obj()),
        }
    }
}

impl<T> ComponentMsgObj for MnemonicKeyboard<T>
where
    T: MnemonicInput,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            MnemonicKeyboardMsg::Confirmed => {
                if let Some(word) = self.mnemonic() {
                    word.try_into()
                } else {
                    fatal_error!("Invalid mnemonic")
                }
            }
            MnemonicKeyboardMsg::Previous => "".try_into(),
        }
    }
}

impl<T> ComponentMsgObj for Frame<T>
where
    T: ComponentMsgObj,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            FrameMsg::Content(c) => self.inner().msg_try_into_obj(c),
            FrameMsg::Button(b) => b.try_into(),
        }
    }
}

impl ComponentMsgObj for SelectWordCount {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            SelectWordCountMsg::Selected(n) => n.try_into(),
        }
    }
}

impl ComponentMsgObj for VerticalMenu {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            VerticalMenuChoiceMsg::Selected(i) => i.try_into(),
        }
    }
}

impl ComponentMsgObj for StatusScreen {
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        Ok(CONFIRMED.as_obj())
    }
}

impl ComponentMsgObj for PromptScreen {
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        Ok(CONFIRMED.as_obj())
    }
}

impl<T: Component + ComponentMsgObj> ComponentMsgObj for SwipeContent<T> {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        self.inner().msg_try_into_obj(msg)
    }
}

impl<T: Component + ComponentMsgObj + Swipable> ComponentMsgObj for SwipeUpScreen<T> {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            SwipeUpScreenMsg::Content(c) => self.inner().msg_try_into_obj(c),
            SwipeUpScreenMsg::Swiped => Ok(CONFIRMED.as_obj()),
        }
    }
}

// Clippy/compiler complains about conflicting implementations
// TODO move the common impls to a common module
#[cfg(not(feature = "clippy"))]
impl<'a, T> ComponentMsgObj for Paragraphs<T>
where
    T: ParagraphSource<'a>,
{
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!()
    }
}

impl ComponentMsgObj for Progress {
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!()
    }
}

impl ComponentMsgObj for Homescreen {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            HomescreenMsg::Dismissed => Ok(CANCELLED.as_obj()),
        }
    }
}

impl ComponentMsgObj for Lockscreen {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            HomescreenMsg::Dismissed => Ok(CANCELLED.as_obj()),
        }
    }
}

// Clippy/compiler complains about conflicting implementations
#[cfg(not(feature = "clippy"))]
impl<T> ComponentMsgObj for (Timeout, T)
where
    T: Component<Msg = ()>,
{
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        Ok(CANCELLED.as_obj())
    }
}

impl ComponentMsgObj for AddressDetails {
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        Ok(CANCELLED.as_obj())
    }
}

impl<U> ComponentMsgObj for CoinJoinProgress<U>
where
    U: Component<Msg = Never>,
{
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!();
    }
}

extern "C" fn new_confirm_emphasized(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;

        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;
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

        new_confirm_action_simple(
            FormattedText::new(ops).vertically_centered(),
            ConfirmActionExtra::Menu(ConfirmActionMenuStrings::new()),
            ConfirmActionStrings::new(title, None, None, Some(title)),
            false,
            None,
            0,
            false,
        )
        .and_then(LayoutObj::new_root)
        .map(Into::into)
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
        let info: bool = kwargs.get_or(Qstr::MP_QSTR_info, true)?;
        let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;
        let chunkify: bool = kwargs.get_or(Qstr::MP_QSTR_chunkify, false)?;
        let page_counter: bool = kwargs.get_or(Qstr::MP_QSTR_page_counter, false)?;
        let prompt_screen: bool = kwargs.get_or(Qstr::MP_QSTR_prompt_screen, true)?;
        let cancel: bool = kwargs.get_or(Qstr::MP_QSTR_cancel, false)?;

        ConfirmBlobParams::new(title, data, description)
            .with_subtitle(subtitle)
            .with_verb(verb)
            .with_verb_cancel(verb_cancel.unwrap_or(TR::buttons__cancel.into()))
            .with_verb_info(if info { Some(TR::words__title_information.into()) } else { None })
            .with_extra(extra)
            .with_chunkify(chunkify)
            .with_page_counter(page_counter)
            .with_cancel(cancel)
            .with_prompt(prompt_screen)
            .with_hold(hold)
            .into_flow()
            .and_then(LayoutObj::new_root)
            .map(Into::into)
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

        ConfirmBlobParams::new(title, data, Some(TR::instructions__view_all_data.into()))
            .with_verb(verb)
            .with_verb_info(Some(TR::buttons__view_all_data.into()))
            .with_description_font(&theme::TEXT_SUB_GREEN_LIME)
            .with_subtitle(subtitle)
            .with_verb_cancel(verb_cancel.unwrap_or(TR::buttons__cancel.into()))
            .with_footer_description(Some(
                TR::buttons__confirm.into(), /* or words__confirm?? */
            ))
            .with_chunkify(chunkify)
            .with_page_limit(Some(1))
            .with_frame_margin(CONFIRM_BLOB_INTRO_MARGIN)
            .into_flow()
            .and_then(LayoutObj::new_root)
            .map(Into::into)
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_action(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let action: Option<TString> = kwargs.get(Qstr::MP_QSTR_action)?.try_into_option()?;
        let description: Option<TString> =
            kwargs.get(Qstr::MP_QSTR_description)?.try_into_option()?;
        let subtitle: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_subtitle)
            .unwrap_or(Obj::const_none())
            .try_into_option()?;
        let verb_cancel: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_verb_cancel)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let reverse: bool = kwargs.get_or(Qstr::MP_QSTR_reverse, false)?;
        let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;
        let prompt_screen: bool = kwargs.get_or(Qstr::MP_QSTR_prompt_screen, false)?;
        let prompt_title: TString = kwargs.get_or(Qstr::MP_QSTR_prompt_title, title)?;

        let flow = flow::confirm_action::new_confirm_action(
            title,
            action,
            description,
            subtitle,
            verb_cancel,
            reverse,
            hold,
            prompt_screen,
            prompt_title,
        )?;
        Ok(LayoutObj::new_root(flow)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}
extern "C" fn new_confirm_address(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: Option<TString> =
            kwargs.get(Qstr::MP_QSTR_description)?.try_into_option()?;
        let extra: Option<TString> = kwargs.get(Qstr::MP_QSTR_extra)?.try_into_option()?;
        let data: Obj = kwargs.get(Qstr::MP_QSTR_data)?;
        let chunkify: bool = kwargs.get_or(Qstr::MP_QSTR_chunkify, false)?;

        let data_style = if chunkify {
            let address: TString = data.try_into()?;
            theme::get_chunkified_text_style(address.len())
        } else {
            &theme::TEXT_MONO
        };

        let paragraphs = ConfirmBlob {
            description: description.unwrap_or("".into()),
            extra: extra.unwrap_or("".into()),
            data: data.try_into()?,
            description_font: &theme::TEXT_NORMAL,
            extra_font: &theme::TEXT_DEMIBOLD,
            data_font: data_style,
        }
        .into_paragraphs();

        flow::new_confirm_action_simple(
            paragraphs,
            ConfirmActionExtra::Menu(ConfirmActionMenuStrings::new()),
            ConfirmActionStrings::new(title, None, None, None),
            false,
            None,
            0,
            false,
        )
        .and_then(LayoutObj::new_root)
        .map(Into::into)
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

        let flow =
            flow::confirm_firmware_update::new_confirm_firmware_update(description, fingerprint)?;
        Ok(LayoutObj::new_root(flow)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_properties(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;

        let paragraphs = PropsList::new(
            items,
            &theme::TEXT_NORMAL,
            &theme::TEXT_MONO,
            &theme::TEXT_MONO,
        )?;

        new_confirm_action_simple(
            paragraphs.into_paragraphs(),
            ConfirmActionExtra::Menu(ConfirmActionMenuStrings::new()),
            ConfirmActionStrings::new(title, None, None, hold.then_some(title)),
            hold,
            None,
            0,
            false,
        )
        .and_then(LayoutObj::new_root)
        .map(Into::into)
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_homescreen(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let image: Obj = kwargs.get(Qstr::MP_QSTR_image)?;

        let jpeg: BinaryData = image.try_into()?;

        let obj = if jpeg.is_empty() {
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
            )
            .and_then(LayoutObj::new_root)
            .map(Into::into)
        } else {
            if !check_homescreen_format(jpeg) {
                return Err(value_error!(c"Invalid image."));
            };

            let obj = LayoutObj::new(SwipeUpScreen::new(
                Frame::left_aligned(title, SwipeContent::new(CachedJpeg::new(jpeg, 1)))
                    .with_cancel_button()
                    .with_footer(
                        TR::instructions__swipe_up.into(),
                        Some(TR::buttons__change.into()),
                    )
                    .with_swipe(Direction::Up, SwipeSettings::default()),
            ));
            Ok(obj?.into())
        };
        obj
    };

    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_reset(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let recovery: bool = kwargs.get(Qstr::MP_QSTR_recovery)?.try_into()?;

        let flow = flow::confirm_reset::new_confirm_reset(recovery)?;
        Ok(LayoutObj::new_root(flow)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_set_new_pin(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: TString = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;

        let flow = flow::confirm_set_new_pin::new_set_new_pin(title, description)?;
        Ok(LayoutObj::new_root(flow)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_output(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: Option<TString> = kwargs.get(Qstr::MP_QSTR_title)?.try_into_option()?;
        let subtitle: Option<TString> = kwargs.get(Qstr::MP_QSTR_subtitle)?.try_into_option()?;

        let account: Option<TString> = kwargs.get(Qstr::MP_QSTR_account)?.try_into_option()?;
        let account_path: Option<TString> =
            kwargs.get(Qstr::MP_QSTR_account_path)?.try_into_option()?;

        let br_name: TString = kwargs.get(Qstr::MP_QSTR_br_name)?.try_into()?;
        let br_code: u16 = kwargs.get(Qstr::MP_QSTR_br_code)?.try_into()?;

        let message: Obj = kwargs.get(Qstr::MP_QSTR_message)?;
        let amount: Option<Obj> = kwargs.get(Qstr::MP_QSTR_amount)?.try_into_option()?;

        let chunkify: bool = kwargs.get_or(Qstr::MP_QSTR_chunkify, false)?;
        let text_mono: bool = kwargs.get_or(Qstr::MP_QSTR_text_mono, true)?;

        let address: Option<Obj> = kwargs.get(Qstr::MP_QSTR_address)?.try_into_option()?;
        let address_title: Option<TString> =
            kwargs.get(Qstr::MP_QSTR_address_title)?.try_into_option()?;

        let summary_items: Option<Obj> =
            kwargs.get(Qstr::MP_QSTR_summary_items)?.try_into_option()?;
        let fee_items: Option<Obj> = kwargs.get(Qstr::MP_QSTR_fee_items)?.try_into_option()?;

        let summary_title: Option<TString> =
            kwargs.get(Qstr::MP_QSTR_summary_title)?.try_into_option()?;
        let summary_br_name: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_summary_br_name)?
            .try_into_option()?;
        let summary_br_code: Option<u16> = kwargs
            .get(Qstr::MP_QSTR_summary_br_code)?
            .try_into_option()?;

        let address_title = address_title.unwrap_or(TR::words__address.into());
        let cancel_text: Option<TString> =
            kwargs.get(Qstr::MP_QSTR_cancel_text)?.try_into_option()?;

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
        Ok(LayoutObj::new_root(flow)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_summary(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;
        let account_items: Obj = kwargs.get(Qstr::MP_QSTR_account_items)?;
        let account_items_title: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_account_items_title)
            .unwrap_or(Obj::const_none())
            .try_into_option()?;
        let fee_items: Obj = kwargs.get(Qstr::MP_QSTR_fee_items)?;
        let br_name: TString = kwargs.get(Qstr::MP_QSTR_br_name)?.try_into()?;
        let br_code: u16 = kwargs.get(Qstr::MP_QSTR_br_code)?.try_into()?;
        let cancel_text: Option<TString> =
            kwargs.get(Qstr::MP_QSTR_cancel_text)?.try_into_option()?;

        let mut summary_params = ShowInfoParams::new(title)
            .with_menu_button()
            .with_footer(TR::instructions__swipe_up.into(), None)
            .with_swipe_up();
        for pair in IterBuf::new().try_iterate(items)? {
            let [label, value]: [TString; 2] = util::iter_into_array(pair)?;
            summary_params = unwrap!(summary_params.add(label, value));
        }

        let mut account_params =
            ShowInfoParams::new(account_items_title.unwrap_or(TR::send__send_from.into()))
                .with_cancel_button();
        for pair in IterBuf::new().try_iterate(account_items)? {
            let [label, value]: [TString; 2] = util::iter_into_array(pair)?;
            account_params = unwrap!(account_params.add(label, value));
        }

        let mut fee_params =
            ShowInfoParams::new(TR::confirm_total__title_fee.into()).with_cancel_button();
        for pair in IterBuf::new().try_iterate(fee_items)? {
            let [label, value]: [TString; 2] = util::iter_into_array(pair)?;
            fee_params = unwrap!(fee_params.add(label, value));
        }

        let flow = flow::new_confirm_summary(
            summary_params,
            account_params,
            fee_params,
            br_name,
            br_code,
            cancel_text,
        )?;
        Ok(LayoutObj::new_root(flow)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_set_brightness(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let current: u8 = kwargs.get(Qstr::MP_QSTR_current)?.try_into()?;
        let flow = flow::set_brightness::new_set_brightness(current)?;
        Ok(LayoutObj::new_root(flow)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_info_with_cancel(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;
        let _horizontal: bool = kwargs.get_or(Qstr::MP_QSTR_horizontal, false)?; // FIXME
        let chunkify: bool = kwargs.get_or(Qstr::MP_QSTR_chunkify, false)?;

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

        let obj = LayoutObj::new(SwipeUpScreen::new(
            Frame::left_aligned(title, SwipeContent::new(paragraphs.into_paragraphs()))
                .with_cancel_button(),
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_value(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let subtitle: Option<TString> = kwargs.get(Qstr::MP_QSTR_subtitle)?.try_into_option()?;
        let description: Option<TString> =
            kwargs.get(Qstr::MP_QSTR_description)?.try_into_option()?;
        let value: Obj = kwargs.get(Qstr::MP_QSTR_value)?;
        let info_button: bool = kwargs.get_or(Qstr::MP_QSTR_info_button, false)?;

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
        let text_mono: bool = kwargs.get_or(Qstr::MP_QSTR_text_mono, true)?;

        ConfirmBlobParams::new(title, value, description)
            .with_subtitle(subtitle)
            .with_verb(verb)
            .with_verb_cancel(verb_cancel.unwrap_or(TR::buttons__cancel.into()))
            .with_verb_info(if info_button {
                Some(TR::words__title_information.into())
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
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_total(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;

        let mut paragraphs = ParagraphVecShort::new();

        for pair in IterBuf::new().try_iterate(items)? {
            let [label, value]: [TString; 2] = util::iter_into_array(pair)?;
            paragraphs.add(Paragraph::new(&theme::TEXT_NORMAL, label).no_break());
            paragraphs.add(Paragraph::new(&theme::TEXT_MONO, value));
        }

        new_confirm_action_simple(
            paragraphs.into_paragraphs(),
            ConfirmActionExtra::Menu(ConfirmActionMenuStrings::new()),
            ConfirmActionStrings::new(title, None, None, Some(title)),
            true,
            None,
            0,
            false,
        )
        .and_then(LayoutObj::new_root)
        .map(Into::into)
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_modify_output(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let sign: i32 = kwargs.get(Qstr::MP_QSTR_sign)?.try_into()?;
        let amount_change: TString = kwargs.get(Qstr::MP_QSTR_amount_change)?.try_into()?;
        let amount_new: TString = kwargs.get(Qstr::MP_QSTR_amount_new)?.try_into()?;

        let description = if sign < 0 {
            TR::modify_amount__decrease_amount
        } else {
            TR::modify_amount__increase_amount
        };

        let paragraphs = ParagraphVecShort::from_iter([
            Paragraph::new(&theme::TEXT_NORMAL, description),
            Paragraph::new(&theme::TEXT_MONO, amount_change),
            Paragraph::new(&theme::TEXT_NORMAL, TR::modify_amount__new_amount),
            Paragraph::new(&theme::TEXT_MONO, amount_new),
        ])
        .into_paragraphs();

        let obj = LayoutObj::new(SwipeUpScreen::new(
            Frame::left_aligned(TR::modify_amount__title.into(), paragraphs)
                .with_cancel_button()
                .with_footer(TR::instructions__swipe_up.into(), None)
                .with_swipe(Direction::Up, SwipeSettings::default()),
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_modify_fee(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let sign: i32 = kwargs.get(Qstr::MP_QSTR_sign)?.try_into()?;
        let user_fee_change: TString = kwargs.get(Qstr::MP_QSTR_user_fee_change)?.try_into()?;
        let total_fee_new: TString = kwargs.get(Qstr::MP_QSTR_total_fee_new)?.try_into()?;

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
            Paragraph::new(&theme::TEXT_NORMAL, description),
            Paragraph::new(&theme::TEXT_MONO, change),
            Paragraph::new(&theme::TEXT_NORMAL, total_label),
            Paragraph::new(&theme::TEXT_MONO, total_fee_new),
        ])
        .into_paragraphs();

        let obj = LayoutObj::new(SwipeUpScreen::new(
            Frame::left_aligned(title, paragraphs)
                .with_menu_button()
                .with_footer(TR::instructions__swipe_up.into(), None)
                .with_swipe(Direction::Up, SwipeSettings::default()),
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_error(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: TString = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let allow_cancel: bool = kwargs.get(Qstr::MP_QSTR_allow_cancel)?.try_into()?;

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

        let frame = SwipeUpScreen::new(frame);
        Ok(LayoutObj::new(frame)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_share_words(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let subtitle: TString = kwargs.get(Qstr::MP_QSTR_subtitle)?.try_into()?;
        let share_words_obj: Obj = kwargs.get(Qstr::MP_QSTR_words)?;
        let share_words_vec: Vec<TString, 33> = util::iter_into_vec(share_words_obj)?;
        let description: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_description)?
            .try_into_option()?
            .and_then(|desc: TString| if desc.is_empty() { None } else { Some(desc) });
        let text_info: Obj = kwargs.get(Qstr::MP_QSTR_text_info)?;
        let text_confirm: TString = kwargs.get(Qstr::MP_QSTR_text_confirm)?.try_into()?;

        let mut instructions_paragraphs = ParagraphVecShort::new();
        for item in IterBuf::new().try_iterate(text_info)? {
            let text: TString = item.try_into()?;
            instructions_paragraphs.add(Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, text));
        }

        let flow = flow::show_share_words::new_show_share_words(
            title,
            subtitle,
            share_words_vec,
            description,
            instructions_paragraphs,
            text_confirm,
        )?;
        Ok(LayoutObj::new_root(flow)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_warning(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: TString = kwargs.get_or(Qstr::MP_QSTR_description, "".into())?;
        let value: TString = kwargs.get_or(Qstr::MP_QSTR_value, "".into())?;
        let action: Option<TString> = kwargs.get(Qstr::MP_QSTR_button)?.try_into_option()?;
        let danger: bool = kwargs.get_or(Qstr::MP_QSTR_danger, false)?;

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

        Ok(LayoutObj::new(SwipeUpScreen::new(frame_with_icon))?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_success(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_description)?
            .try_into_option()?
            .and_then(|desc: TString| if desc.is_empty() { None } else { Some(desc) });

        let content = StatusScreen::new_success(title);
        let obj = LayoutObj::new(SwipeUpScreen::new(
            Frame::left_aligned(
                TR::words__title_success.into(),
                SwipeContent::new(content).with_no_attach_anim(),
            )
            .with_footer(TR::instructions__swipe_up.into(), description)
            .with_result_icon(ICON_BULLET_CHECKMARK, theme::GREEN_LIGHT)
            .with_swipe(Direction::Up, SwipeSettings::default()),
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_info(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: TString = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let content = Paragraphs::new(Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, description));
        let obj = LayoutObj::new(SwipeUpScreen::new(
            Frame::left_aligned(title, SwipeContent::new(content))
                .with_footer(TR::instructions__swipe_up.into(), None)
                .with_swipe(Direction::Up, SwipeSettings::default()),
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_mismatch(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: TString = TR::addr_mismatch__contact_support_at.into();
        let url: TString = TR::addr_mismatch__support_url.into();
        let button: TString = TR::buttons__quit.into();

        let paragraphs = ParagraphVecShort::from_iter([
            Paragraph::new(&theme::TEXT_NORMAL, description).centered(),
            Paragraph::new(&theme::TEXT_DEMIBOLD, url).centered(),
        ])
        .into_paragraphs();

        let obj = LayoutObj::new(SwipeUpScreen::new(
            Frame::left_aligned(title, SwipeContent::new(paragraphs))
                .with_cancel_button()
                .with_footer(TR::instructions__swipe_up.into(), Some(button))
                .with_swipe(Direction::Up, SwipeSettings::default()),
        ))?;

        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_simple(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let description: TString = kwargs.get_or(Qstr::MP_QSTR_description, "".into())?;

        let obj = LayoutObj::new(Border::new(
            theme::borders(),
            Paragraphs::new(Paragraph::new(&theme::TEXT_DEMIBOLD, description)),
        ))?;

        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_with_info(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let button: TString = kwargs.get(Qstr::MP_QSTR_button)?.try_into()?;
        let info_button: TString = kwargs.get(Qstr::MP_QSTR_info_button)?.try_into()?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;

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

        let flow =
            confirm_with_info::new_confirm_with_info(title, button, info_button, paragraphs)?;
        Ok(LayoutObj::new_root(flow)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_coinjoin(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let max_rounds: TString = kwargs.get(Qstr::MP_QSTR_max_rounds)?.try_into()?;
        let max_feerate: TString = kwargs.get(Qstr::MP_QSTR_max_feerate)?.try_into()?;

        let paragraphs = ParagraphVecShort::from_iter([
            Paragraph::new(&theme::TEXT_NORMAL, TR::coinjoin__max_rounds),
            Paragraph::new(&theme::TEXT_MONO, max_rounds),
            Paragraph::new(&theme::TEXT_NORMAL, TR::coinjoin__max_mining_fee),
            Paragraph::new(&theme::TEXT_MONO, max_feerate),
        ])
        .into_paragraphs();

        new_confirm_action_simple(
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
        )
        .and_then(LayoutObj::new_root)
        .map(Into::into)
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_continue_recovery(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let first_screen: bool = kwargs.get(Qstr::MP_QSTR_first_screen)?.try_into()?;
        let recovery_type: RecoveryType = kwargs.get(Qstr::MP_QSTR_recovery_type)?.try_into()?;
        let text: TString = kwargs.get(Qstr::MP_QSTR_text)?.try_into()?; // #shares entered
        let subtext: Option<TString> = kwargs.get(Qstr::MP_QSTR_subtext)?.try_into_option()?; // #shares remaining
        let pages: Option<Obj> = kwargs.get(Qstr::MP_QSTR_pages)?.try_into_option()?; // info about remaining shares

        let pages_vec = if let Some(pages_obj) = pages {
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

        let flow = flow::continue_recovery::new_continue_recovery(
            first_screen,
            recovery_type,
            text,
            subtext,
            pages_vec,
        )?;
        Ok(LayoutObj::new_root(flow)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_get_address(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
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
        let br_name: TString = kwargs.get(Qstr::MP_QSTR_br_name)?.try_into()?;
        let br_code: u16 = kwargs.get(Qstr::MP_QSTR_br_code)?.try_into()?;

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
            br_code,
            br_name,
        )?;
        Ok(LayoutObj::new_root(flow)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_prompt_backup() -> Obj {
    let block = || {
        let flow = flow::prompt_backup::new_prompt_backup()?;
        let obj = LayoutObj::new_root(flow)?;
        Ok(obj.into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn new_request_number(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let count: u32 = kwargs.get(Qstr::MP_QSTR_count)?.try_into()?;
        let min_count: u32 = kwargs.get(Qstr::MP_QSTR_min_count)?.try_into()?;
        let max_count: u32 = kwargs.get(Qstr::MP_QSTR_max_count)?.try_into()?;
        let description: TString = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let info_cb: Obj = kwargs.get(Qstr::MP_QSTR_info)?;
        assert!(info_cb != Obj::const_none());
        let br_code: u16 = kwargs.get(Qstr::MP_QSTR_br_code)?.try_into()?;
        let br_name: TString = kwargs.get(Qstr::MP_QSTR_br_name)?.try_into()?;

        let mp_info_closure = move |num: u32| {
            // TODO: Handle error
            let text = info_cb
                .call_with_n_args(&[num.try_into().unwrap()])
                .unwrap();
            TString::try_from(text).unwrap()
        };

        let flow = flow::request_number::new_request_number(
            title,
            count,
            min_count,
            max_count,
            description,
            mp_info_closure,
            br_code,
            br_name,
        )?;
        Ok(LayoutObj::new_root(flow)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_passphrase(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let _prompt: TString = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let _max_len: usize = kwargs.get(Qstr::MP_QSTR_max_len)?.try_into()?;

        let flow = flow::request_passphrase::new_request_passphrase()?;
        Ok(LayoutObj::new_root(flow)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_pin(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let prompt: TString = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let subprompt: TString = kwargs.get(Qstr::MP_QSTR_subprompt)?.try_into()?;
        let allow_cancel: bool = kwargs.get_or(Qstr::MP_QSTR_allow_cancel, true)?;
        let warning: bool = kwargs.get_or(Qstr::MP_QSTR_wrong_pin, false)?;
        let warning = if warning {
            Some(TR::pin__wrong_pin.into())
        } else {
            None
        };
        Ok(LayoutObj::new(PinKeyboard::new(prompt, subprompt, warning, allow_cancel))?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_bip39(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let prompt: TString = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let prefill_word: TString = kwargs.get(Qstr::MP_QSTR_prefill_word)?.try_into()?;
        let can_go_back: bool = kwargs.get(Qstr::MP_QSTR_can_go_back)?.try_into()?;
        let obj = LayoutObj::new(MnemonicKeyboard::new(
            prefill_word.map(Bip39Input::prefilled_word),
            prompt,
            can_go_back,
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_slip39(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let prompt: TString = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let prefill_word: TString = kwargs.get(Qstr::MP_QSTR_prefill_word)?.try_into()?;
        let can_go_back: bool = kwargs.get(Qstr::MP_QSTR_can_go_back)?.try_into()?;
        let obj = LayoutObj::new(MnemonicKeyboard::new(
            prefill_word.map(Slip39Input::prefilled_word),
            prompt,
            can_go_back,
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_select_word(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: TString = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let words_iterable: Obj = kwargs.get(Qstr::MP_QSTR_words)?;
        let words: [TString; 3] = util::iter_into_array(words_iterable)?;

        let content = VerticalMenu::select_word(words);
        let frame_with_menu = Frame::left_aligned(title, content).with_subtitle(description);
        Ok(LayoutObj::new(frame_with_menu)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_checklist(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let _button: TString = kwargs.get(Qstr::MP_QSTR_button)?.try_into()?;
        let active: usize = kwargs.get(Qstr::MP_QSTR_active)?.try_into()?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;

        let mut paragraphs = ParagraphVecLong::new();
        for (i, item) in IterBuf::new().try_iterate(items)?.enumerate() {
            let style = match i.cmp(&active) {
                Ordering::Less => &theme::TEXT_CHECKLIST_DONE,
                Ordering::Equal => &theme::TEXT_CHECKLIST_SELECTED,
                Ordering::Greater => &theme::TEXT_CHECKLIST_DEFAULT,
            };
            let text: TString = item.try_into()?;
            paragraphs.add(Paragraph::new(style, text));
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

        let obj = LayoutObj::new(SwipeUpScreen::new(
            Frame::left_aligned(title, SwipeContent::new(checklist_content))
                .with_footer(TR::instructions__swipe_up.into(), None)
                .with_swipe(Direction::Up, SwipeSettings::default()),
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_tutorial() -> Obj {
    let block = || {
        let flow = flow::show_tutorial::new_show_tutorial()?;
        let obj = LayoutObj::new_root(flow)?;
        Ok(obj.into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn new_select_word_count(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let recovery_type: RecoveryType = kwargs.get(Qstr::MP_QSTR_recovery_type)?.try_into()?;
        let content = if matches!(recovery_type, RecoveryType::UnlockRepeatedBackup) {
            SelectWordCount::new_multishare()
        } else {
            SelectWordCount::new_all()
        };
        let obj = LayoutObj::new(Frame::left_aligned(
            TR::recovery__num_of_words.into(),
            content,
        ))?;
        Ok(obj.into())
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
        let lines: [TString; 4] = util::iter_into_array(lines_iterable)?;

        let paragraphs = ParagraphVecShort::from_iter([
            Paragraph::new(&theme::TEXT_NORMAL_GREY_EXTRA_LIGHT, lines[0]).centered(),
            Paragraph::new(&theme::TEXT_DEMIBOLD, lines[1]).centered(),
            Paragraph::new(&theme::TEXT_NORMAL_GREY_EXTRA_LIGHT, lines[2]).centered(),
            Paragraph::new(&theme::TEXT_DEMIBOLD, lines[3]).centered(),
        ])
        .into_paragraphs()
        .with_placement(geometry::LinearPlacement::vertical().align_at_center());

        let obj = LayoutObj::new(SwipeUpScreen::new(
            Frame::left_aligned("".into(), SwipeContent::new(paragraphs))
                .with_footer(TR::instructions__swipe_up.into(), None)
                .with_swipe(Direction::Up, SwipeSettings::default()),
        ))?;

        Ok(obj.into())
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

        let (title, description) = if let Some(title) = title {
            (title, description)
        } else {
            (description, "".into())
        };

        Ok(LayoutObj::new(Progress::new(title, indeterminate, description))?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_progress_coinjoin(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let indeterminate: bool = kwargs.get_or(Qstr::MP_QSTR_indeterminate, false)?;
        let time_ms: u32 = kwargs.get_or(Qstr::MP_QSTR_time_ms, 0)?;
        let skip_first_paint: bool = kwargs.get_or(Qstr::MP_QSTR_skip_first_paint, false)?;

        // The second type parameter is actually not used in `new()` but we need to
        // provide it.
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
        Ok(obj.into())
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

        let notification = notification.map(|w| (w, notification_level));
        let obj = LayoutObj::new(Homescreen::new(label, notification, hold))?;
        if skip_first_paint {
            obj.skip_first_paint();
        }
        Ok(obj.into())
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

        let obj = LayoutObj::new(Lockscreen::new(label, bootscreen, coinjoin_authorized))?;
        if skip_first_paint {
            obj.skip_first_paint();
        }
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

pub extern "C" fn upy_check_homescreen_format(data: Obj) -> Obj {
    let block = || {
        let buffer = data.try_into()?;
        Ok(check_homescreen_format(buffer).into())
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn new_show_wait_text(message: Obj) -> Obj {
    let block = || {
        let message: TString<'static> = message.try_into()?;
        Ok(LayoutObj::new(Connect::new(message, theme::FG, theme::BG))?.into())
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn new_confirm_fido(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    #[cfg(feature = "universal_fw")]
    return flow::confirm_fido::new_confirm_fido(n_args, args, kwargs);
    #[cfg(not(feature = "universal_fw"))]
    panic!();
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

        let flow =
            flow::danger::new_show_danger(title, description, value, verb_cancel)?;
        Ok(LayoutObj::new_root(flow)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

#[no_mangle]
pub static mp_module_trezorui2: Module = obj_module! {
    /// from trezor import utils
    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezorui2.to_obj(),

    /// CONFIRMED: UiResult
    Qstr::MP_QSTR_CONFIRMED => CONFIRMED.as_obj(),

    /// CANCELLED: UiResult
    Qstr::MP_QSTR_CANCELLED => CANCELLED.as_obj(),

    /// INFO: UiResult
    Qstr::MP_QSTR_INFO => INFO.as_obj(),

    /// def disable_animation(disable: bool) -> None:
    ///     """Disable animations, debug builds only."""
    Qstr::MP_QSTR_disable_animation => obj_fn_1!(upy_disable_animation).as_obj(),

    /// def check_homescreen_format(data: bytes) -> bool:
    ///     """Check homescreen format and dimensions."""
    Qstr::MP_QSTR_check_homescreen_format => obj_fn_1!(upy_check_homescreen_format).as_obj(),

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

    /// def confirm_emphasized(
    ///     *,
    ///     title: str,
    ///     items: Iterable[str | tuple[bool, str]],
    ///     verb: str | None = None,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm formatted text that has been pre-split in python. For tuples
    ///     the first component is a bool indicating whether this part is emphasized."""
    Qstr::MP_QSTR_confirm_emphasized => obj_fn_kw!(0, new_confirm_emphasized).as_obj(),

    /// def confirm_homescreen(
    ///     *,
    ///     title: str,
    ///     image: bytes,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm homescreen."""
    Qstr::MP_QSTR_confirm_homescreen => obj_fn_kw!(0, new_confirm_homescreen).as_obj(),

    /// def confirm_blob(
    ///     *,
    ///     title: str,
    ///     data: str | bytes,
    ///     description: str | None,
    ///     extra: str | None = None,
    ///     subtitle: str | None = None,
    ///     verb: str | None = None,
    ///     verb_cancel: str | None = None,
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

    /// def confirm_address(
    ///     *,
    ///     title: str,
    ///     data: str | bytes,
    ///     description: str | None,
    ///     verb: str | None = "CONFIRM",
    ///     extra: str | None,
    ///     chunkify: bool = False,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm address. Similar to `confirm_blob` but has corner info button
    ///     and allows left swipe which does the same thing as the button."""
    Qstr::MP_QSTR_confirm_address => obj_fn_kw!(0, new_confirm_address).as_obj(),

    /// def confirm_properties(
    ///     *,
    ///     title: str,
    ///     items: list[tuple[str | None, str | bytes | None, bool]],
    ///     hold: bool = False,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm list of key-value pairs. The third component in the tuple should be True if
    ///     the value is to be rendered as binary with monospace font, False otherwise."""
    Qstr::MP_QSTR_confirm_properties => obj_fn_kw!(0, new_confirm_properties).as_obj(),

    /// def flow_confirm_reset(recovery: bool) -> LayoutObj[UiResult]:
    ///     """Confirm TOS before creating wallet creation or wallet recovery."""
    Qstr::MP_QSTR_flow_confirm_reset => obj_fn_kw!(0, new_confirm_reset).as_obj(),

    // TODO: supply more arguments for Wipe code setting when figma done
    /// def flow_confirm_set_new_pin(
    ///     *,
    ///     title: str,
    ///     description: str,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm new PIN setup with an option to cancel action."""
    Qstr::MP_QSTR_flow_confirm_set_new_pin => obj_fn_kw!(0, new_confirm_set_new_pin).as_obj(),

    /// def show_info_with_cancel(
    ///     *,
    ///     title: str,
    ///     items: Iterable[Tuple[str, str]],
    ///     horizontal: bool = False,
    ///     chunkify: bool = False,
    /// ) -> LayoutObj[UiResult]:
    ///     """Show metadata for outgoing transaction."""
    Qstr::MP_QSTR_show_info_with_cancel => obj_fn_kw!(0, new_show_info_with_cancel).as_obj(),

    /// def confirm_value(
    ///     *,
    ///     title: str,
    ///     value: str,
    ///     description: str | None,
    ///     subtitle: str | None,
    ///     verb: str | None = None,
    ///     verb_cancel: str | None = None,
    ///     info_button: bool = False,
    ///     hold: bool = False,
    ///     chunkify: bool = False,
    ///     text_mono: bool = True,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm value. Merge of confirm_total and confirm_output."""
    Qstr::MP_QSTR_confirm_value => obj_fn_kw!(0, new_confirm_value).as_obj(),

    /// def confirm_total(
    ///     *,
    ///     title: str,
    ///     items: Iterable[tuple[str, str]],
    ///     info_button: bool = False,
    ///     cancel_arrow: bool = False,
    /// ) -> LayoutObj[UiResult]:
    ///     """Transaction summary. Always hold to confirm."""
    Qstr::MP_QSTR_confirm_total => obj_fn_kw!(0, new_confirm_total).as_obj(),

    /// def confirm_modify_output(
    ///     *,
    ///     sign: int,
    ///     amount_change: str,
    ///     amount_new: str,
    /// ) -> LayoutObj[UiResult]:
    ///     """Decrease or increase output amount."""
    Qstr::MP_QSTR_confirm_modify_output => obj_fn_kw!(0, new_confirm_modify_output).as_obj(),

    /// def confirm_modify_fee(
    ///     *,
    ///     title: str,
    ///     sign: int,
    ///     user_fee_change: str,
    ///     total_fee_new: str,
    ///     fee_rate_amount: str | None,  # ignored
    /// ) -> LayoutObj[UiResult]:
    ///     """Decrease or increase transaction fee."""
    Qstr::MP_QSTR_confirm_modify_fee => obj_fn_kw!(0, new_confirm_modify_fee).as_obj(),

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

    /// def show_error(
    ///     *,
    ///     title: str,
    ///     button: str = "CONTINUE",
    ///     description: str = "",
    ///     allow_cancel: bool = False,
    ///     time_ms: int = 0,
    /// ) -> LayoutObj[UiResult]:
    ///     """Error modal. No buttons shown when `button` is empty string."""
    Qstr::MP_QSTR_show_error => obj_fn_kw!(0, new_show_error).as_obj(),

    /// def show_warning(
    ///     *,
    ///     title: str,
    ///     button: str = "CONTINUE",
    ///     value: str = "",
    ///     description: str = "",
    ///     allow_cancel: bool = False,
    ///     time_ms: int = 0,
    ///     danger: bool = False,
    /// ) -> LayoutObj[UiResult]:
    ///     """Warning modal. No buttons shown when `button` is empty string."""
    Qstr::MP_QSTR_show_warning => obj_fn_kw!(0, new_show_warning).as_obj(),

    /// def show_danger(
    ///     *,
    ///     title: str,
    ///     description: str,
    ///     value: str = "",
    ///     verb_cancel: str | None = None,
    /// ) -> LayoutObj[UiResult]:
    ///     """Warning modal that makes it easier to cancel than to continue."""
    Qstr::MP_QSTR_show_danger => obj_fn_kw!(0, new_show_danger).as_obj(),

    /// def show_success(
    ///     *,
    ///     title: str,
    ///     button: str = "CONTINUE",
    ///     description: str = "",
    ///     allow_cancel: bool = False,
    ///     time_ms: int = 0,
    /// ) -> LayoutObj[UiResult]:
    ///     """Success screen. Description is used in the footer."""
    Qstr::MP_QSTR_show_success => obj_fn_kw!(0, new_show_success).as_obj(),

    /// def show_info(
    ///     *,
    ///     title: str,
    ///     button: str = "CONTINUE",
    ///     description: str = "",
    ///     allow_cancel: bool = False,
    ///     time_ms: int = 0,
    /// ) -> LayoutObj[UiResult]:
    ///     """Info modal. No buttons shown when `button` is empty string."""
    Qstr::MP_QSTR_show_info => obj_fn_kw!(0, new_show_info).as_obj(),

    /// def show_mismatch(*, title: str) -> LayoutObj[UiResult]:
    ///     """Warning modal, receiving address mismatch."""
    Qstr::MP_QSTR_show_mismatch => obj_fn_kw!(0, new_show_mismatch).as_obj(),

    /// def show_simple(
    ///     *,
    ///     title: str | None,
    ///     description: str = "",
    ///     button: str = "",
    /// ) -> LayoutObj[UiResult]:
    ///     """Simple dialog with text and one button."""
    Qstr::MP_QSTR_show_simple => obj_fn_kw!(0, new_show_simple).as_obj(),

    /// def confirm_with_info(
    ///     *,
    ///     title: str,
    ///     button: str,
    ///     info_button: str,
    ///     items: Iterable[tuple[int, str]],
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm given items but with third button. In mercury, the button is placed in
    ///     context menu."""
    Qstr::MP_QSTR_confirm_with_info => obj_fn_kw!(0, new_confirm_with_info).as_obj(),

    /// def confirm_coinjoin(
    ///     *,
    ///     max_rounds: str,
    ///     max_feerate: str,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm coinjoin authorization."""
    Qstr::MP_QSTR_confirm_coinjoin => obj_fn_kw!(0, new_confirm_coinjoin).as_obj(),

    /// def request_pin(
    ///     *,
    ///     prompt: str,
    ///     subprompt: str,
    ///     allow_cancel: bool = True,
    ///     wrong_pin: bool = False,
    /// ) -> LayoutObj[str | UiResult]:
    ///     """Request pin on device."""
    Qstr::MP_QSTR_request_pin => obj_fn_kw!(0, new_request_pin).as_obj(),

    /// def flow_request_passphrase(
    ///     *,
    ///     prompt: str,
    ///     max_len: int,
    /// ) -> LayoutObj[str | UiResult]:
    ///     """Passphrase input keyboard."""
    Qstr::MP_QSTR_flow_request_passphrase => obj_fn_kw!(0, new_request_passphrase).as_obj(),

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

    /// def select_word(
    ///     *,
    ///     title: str,
    ///     description: str,
    ///     words: Iterable[str],
    /// ) -> LayoutObj[int]:
    ///     """Select mnemonic word from three possibilities - seed check after backup. The
    ///    iterable must be of exact size. Returns index in range `0..3`."""
    Qstr::MP_QSTR_select_word => obj_fn_kw!(0, new_select_word).as_obj(),

    /// def flow_prompt_backup() -> LayoutObj[UiResult]:
    ///     """Prompt a user to create backup with an option to skip."""
    Qstr::MP_QSTR_flow_prompt_backup => obj_fn_0!(new_prompt_backup).as_obj(),

    /// def flow_show_share_words(
    ///     *,
    ///     title: str,
    ///     subtitle: str,
    ///     words: Iterable[str],
    ///     description: str,
    ///     text_info: Iterable[str],
    ///     text_confirm: str,
    /// ) -> LayoutObj[UiResult]:
    ///     """Show wallet backup words preceded by an instruction screen and followed by
    ///     confirmation."""
    Qstr::MP_QSTR_flow_show_share_words => obj_fn_kw!(0, new_show_share_words).as_obj(),

    /// def flow_request_number(
    ///     *,
    ///     title: str,
    ///     count: int,
    ///     min_count: int,
    ///     max_count: int,
    ///     description: str,
    ///     info: Callable[[int], str] | None = None,
    ///     br_code: ButtonRequestType,
    ///     br_name: str,
    /// ) -> LayoutObj[tuple[UiResult, int]]:
    ///     """Number input with + and - buttons, description, and context menu with cancel and
    ///     info."""
    Qstr::MP_QSTR_flow_request_number => obj_fn_kw!(0, new_request_number).as_obj(),

    /// def set_brightness(
    ///     *,
    ///     current: int | None = None
    /// ) -> LayoutObj[UiResult]:
    ///     """Show the brightness configuration dialog."""
    Qstr::MP_QSTR_set_brightness => obj_fn_kw!(0, new_set_brightness).as_obj(),

    /// def show_checklist(
    ///     *,
    ///     title: str,
    ///     items: Iterable[str],
    ///     active: int,
    ///     button: str,
    /// ) -> LayoutObj[UiResult]:
    ///     """Checklist of backup steps. Active index is highlighted, previous items have check
    ///    mark next to them."""
    Qstr::MP_QSTR_show_checklist => obj_fn_kw!(0, new_show_checklist).as_obj(),

    /// def flow_continue_recovery(
    ///     *,
    ///     first_screen: bool,
    ///     recovery_type: RecoveryType,
    ///     text: str,
    ///     subtext: str | None = None,
    ///     pages: Iterable[tuple[str, str]] | None = None,
    /// ) -> LayoutObj[UiResult]:
    ///     """Device recovery homescreen."""
    Qstr::MP_QSTR_flow_continue_recovery => obj_fn_kw!(0, new_continue_recovery).as_obj(),

    /// def select_word_count(
    ///     *,
    ///     recovery_type: RecoveryType,
    /// ) -> LayoutObj[int | str]:  # merucry returns int
    ///     """Select a mnemonic word count from the options: 12, 18, 20, 24, or 33.
    ///     For unlocking a repeated backup, select from 20 or 33."""
    Qstr::MP_QSTR_select_word_count => obj_fn_kw!(0, new_select_word_count).as_obj(),

    /// def show_group_share_success(
    ///     *,
    ///     lines: Iterable[str]
    /// ) -> LayoutObj[UiResult]:
    ///     """Shown after successfully finishing a group."""
    Qstr::MP_QSTR_show_group_share_success => obj_fn_kw!(0, new_show_group_share_success).as_obj(),

    /// def show_progress(
    ///     *,
    ///     title: str,
    ///     indeterminate: bool = False,
    ///     description: str = "",
    /// ) -> LayoutObj[UiResult]:
    ///     """Show progress loader. Please note that the number of lines reserved on screen for
    ///    description is determined at construction time. If you want multiline descriptions
    ///    make sure the initial description has at least that amount of lines."""
    Qstr::MP_QSTR_show_progress => obj_fn_kw!(0, new_show_progress).as_obj(),

    /// def show_progress_coinjoin(
    ///     *,
    ///     title: str,
    ///     indeterminate: bool = False,
    ///     time_ms: int = 0,
    ///     skip_first_paint: bool = False,
    /// ) -> LayoutObj[UiResult]:
    ///     """Show progress loader for coinjoin. Returns CANCELLED after a specified time when
    ///    time_ms timeout is passed."""
    Qstr::MP_QSTR_show_progress_coinjoin => obj_fn_kw!(0, new_show_progress_coinjoin).as_obj(),

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

    /// def show_lockscreen(
    ///     *,
    ///     label: str | None,
    ///     bootscreen: bool,
    ///     skip_first_paint: bool,
    ///     coinjoin_authorized: bool = False,
    /// ) -> LayoutObj[UiResult]:
    ///     """Homescreen for locked device."""
    Qstr::MP_QSTR_show_lockscreen => obj_fn_kw!(0, new_show_lockscreen).as_obj(),

    /// def confirm_firmware_update(
    ///     *,
    ///     description: str,
    ///     fingerprint: str,
    /// ) -> LayoutObj[UiResult]:
    ///     """Ask whether to update firmware, optionally show fingerprint."""
    Qstr::MP_QSTR_confirm_firmware_update => obj_fn_kw!(0, new_confirm_firmware_update).as_obj(),

    /// def tutorial() -> LayoutObj[UiResult]:
    ///     """Show user how to interact with the device."""
    Qstr::MP_QSTR_tutorial => obj_fn_0!(new_show_tutorial).as_obj(),

    /// def show_wait_text(message: str, /) -> LayoutObj[None]:
    ///     """Show single-line text in the middle of the screen."""
    Qstr::MP_QSTR_show_wait_text => obj_fn_1!(new_show_wait_text).as_obj(),

    /// def flow_get_address(
    ///     *,
    ///     address: str | bytes,
    ///     title: str,
    ///     description: str | None,
    ///     extra: str | None,
    ///     chunkify: bool,
    ///     address_qr: str | None,
    ///     case_sensitive: bool,
    ///     account: str | None,
    ///     path: str | None,
    ///     xpubs: list[tuple[str, str]],
    ///     title_success: str,
    ///     br_code: ButtonRequestType,
    ///     br_name: str,
    /// ) -> LayoutObj[UiResult]:
    ///     """Get address / receive funds."""
    Qstr::MP_QSTR_flow_get_address => obj_fn_kw!(0, new_get_address).as_obj(),

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
    Qstr::MP_QSTR_flow_confirm_output => obj_fn_kw!(0, new_confirm_output).as_obj(),

    /// def flow_confirm_summary(
    ///     *,
    ///     title: str,
    ///     items: Iterable[tuple[str, str]],
    ///     account_items: Iterable[tuple[str, str]],
    ///     account_items_title: str | None,
    ///     fee_items: Iterable[tuple[str, str]],
    ///     br_code: ButtonRequestType,
    ///     br_name: str,
    ///     cancel_text: str | None = None,
    /// ) -> LayoutObj[UiResult]:
    ///     """Total summary and hold to confirm."""
    Qstr::MP_QSTR_flow_confirm_summary => obj_fn_kw!(0, new_confirm_summary).as_obj(),

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
