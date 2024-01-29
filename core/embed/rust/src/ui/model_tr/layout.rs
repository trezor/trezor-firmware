use core::{cmp::Ordering, convert::TryInto};

use heapless::Vec;

use crate::{
    error::Error,
    maybe_trace::MaybeTrace,
    micropython::{
        buffer::{get_buffer, StrBuffer},
        gc::Gc,
        iter::IterBuf,
        list::List,
        map::Map,
        module::Module,
        obj::Obj,
        qstr::Qstr,
        util,
    },
    strutil::{StringType, TString},
    translations::TR,
    trezorhal::model,
    ui::{
        component::{
            base::Component,
            connect::Connect,
            paginated::{PageMsg, Paginate},
            text::{
                op::OpTextLayout,
                paragraphs::{
                    Checklist, Paragraph, ParagraphSource, ParagraphVecLong, ParagraphVecShort,
                    Paragraphs, VecExt,
                },
                TextStyle,
            },
            ComponentExt, FormattedText, Label, LineBreaking, Timeout,
        },
        display, geometry,
        layout::{
            obj::{ComponentMsgObj, LayoutObj},
            result::{CANCELLED, CONFIRMED, INFO},
            util::{upy_disable_animation, ConfirmBlob},
        },
        model_tr::component::check_homescreen_format,
    },
};

use super::{
    component::{
        AddressDetails, ButtonActions, ButtonDetails, ButtonLayout, ButtonPage, CancelConfirmMsg,
        CancelInfoConfirmMsg, CoinJoinProgress, ConfirmHomescreen, Flow, FlowPages, Frame,
        Homescreen, Lockscreen, NumberInput, Page, PassphraseEntry, PinEntry, Progress,
        ScrollableContent, ScrollableFrame, ShareWords, ShowMore, SimpleChoice, WordlistEntry,
        WordlistType,
    },
    constant, theme,
};

impl From<CancelConfirmMsg> for Obj {
    fn from(value: CancelConfirmMsg) -> Self {
        match value {
            CancelConfirmMsg::Cancelled => CANCELLED.as_obj(),
            CancelConfirmMsg::Confirmed => CONFIRMED.as_obj(),
        }
    }
}

impl<T> ComponentMsgObj for ShowMore<T>
where
    T: Component,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            CancelInfoConfirmMsg::Cancelled => Ok(CANCELLED.as_obj()),
            CancelInfoConfirmMsg::Info => Ok(INFO.as_obj()),
            CancelInfoConfirmMsg::Confirmed => Ok(CONFIRMED.as_obj()),
        }
    }
}

impl<T> ComponentMsgObj for Paragraphs<T>
where
    T: ParagraphSource,
{
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!()
    }
}

impl<T> ComponentMsgObj for ButtonPage<T>
where
    T: Component + Paginate,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            PageMsg::Confirmed => Ok(CONFIRMED.as_obj()),
            PageMsg::Cancelled => Ok(CANCELLED.as_obj()),
            _ => Err(Error::TypeError),
        }
    }
}

impl<F, T> ComponentMsgObj for Flow<F, T>
where
    F: Fn(usize) -> Page<T>,
    T: StringType + Clone,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            CancelInfoConfirmMsg::Confirmed => {
                if let Some(index) = self.confirmed_index() {
                    index.try_into()
                } else {
                    Ok(CONFIRMED.as_obj())
                }
            }
            CancelInfoConfirmMsg::Cancelled => Ok(CANCELLED.as_obj()),
            CancelInfoConfirmMsg::Info => Ok(INFO.as_obj()),
        }
    }
}

impl<T> ComponentMsgObj for PinEntry<T>
where
    T: StringType + Clone,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            CancelConfirmMsg::Confirmed => self.pin().try_into(),
            CancelConfirmMsg::Cancelled => Ok(CANCELLED.as_obj()),
        }
    }
}

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

impl<T> ComponentMsgObj for CoinJoinProgress<T>
where
    T: StringType,
{
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!();
    }
}

impl ComponentMsgObj for NumberInput {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        msg.try_into()
    }
}

impl ComponentMsgObj for SimpleChoice {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        if self.return_index {
            msg.try_into()
        } else {
            let text = self.result_by_index(msg);
            text.try_into()
        }
    }
}

impl ComponentMsgObj for WordlistEntry {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        msg.try_into()
    }
}

impl ComponentMsgObj for PassphraseEntry {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            CancelConfirmMsg::Confirmed => self.passphrase().try_into(),
            CancelConfirmMsg::Cancelled => Ok(CANCELLED.as_obj()),
        }
    }
}

impl<T, U> ComponentMsgObj for Frame<T, U>
where
    T: ComponentMsgObj,
    U: StringType + Clone,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        self.inner().msg_try_into_obj(msg)
    }
}

impl<T, U> ComponentMsgObj for ScrollableFrame<T, U>
where
    T: ComponentMsgObj + ScrollableContent,
    U: StringType + Clone,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        self.inner().msg_try_into_obj(msg)
    }
}

impl<T> ComponentMsgObj for Progress<T>
where
    T: StringType,
{
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!()
    }
}

impl<T> ComponentMsgObj for Homescreen<T>
where
    T: StringType + Clone,
{
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        Ok(CANCELLED.as_obj())
    }
}

impl<T> ComponentMsgObj for Lockscreen<T>
where
    T: StringType + Clone,
{
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        Ok(CANCELLED.as_obj())
    }
}

impl<'a, T, F> ComponentMsgObj for ConfirmHomescreen<T, F>
where
    T: StringType + Clone,
    F: Fn() -> &'a [u8],
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            CancelConfirmMsg::Confirmed => Ok(CONFIRMED.as_obj()),
            CancelConfirmMsg::Cancelled => Ok(CANCELLED.as_obj()),
        }
    }
}

impl<U> ComponentMsgObj for super::component::bl_confirm::Confirm<U>
where
    U: AsRef<str>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            super::component::bl_confirm::ConfirmMsg::Cancel => Ok(CANCELLED.as_obj()),
            super::component::bl_confirm::ConfirmMsg::Confirm => Ok(CONFIRMED.as_obj()),
        }
    }
}

/// Function to create and call a `ButtonPage` dialog based on paginable content
/// (e.g. `Paragraphs` or `FormattedText`).
/// Has optional title (supply empty `StrBuffer` for that) and hold-to-confirm
/// functionality.
fn content_in_button_page<T: Component + Paginate + MaybeTrace + 'static>(
    title: StrBuffer,
    content: T,
    verb: TString<'static>,
    verb_cancel: Option<TString<'static>>,
    hold: bool,
) -> Result<Obj, Error> {
    // Left button - icon, text or nothing.
    let cancel_btn = verb_cancel.map(ButtonDetails::from_text_possible_icon);

    // Right button - text or nothing.
    // Optional HoldToConfirm
    let mut confirm_btn = if !verb.is_empty() {
        Some(ButtonDetails::text(verb))
    } else {
        None
    };
    if hold {
        confirm_btn = confirm_btn.map(|btn| btn.with_default_duration());
    }

    let content = ButtonPage::new(content, theme::BG)
        .with_cancel_btn(cancel_btn)
        .with_confirm_btn(confirm_btn);

    let mut frame = ScrollableFrame::new(content);
    if !title.as_ref().is_empty() {
        frame = frame.with_title(title);
    }
    let obj = LayoutObj::new(frame)?;

    Ok(obj.into())
}

extern "C" fn new_confirm_action(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let action: Option<StrBuffer> = kwargs.get(Qstr::MP_QSTR_action)?.try_into_option()?;
        let description: Option<StrBuffer> =
            kwargs.get(Qstr::MP_QSTR_description)?.try_into_option()?;
        let verb: TString<'static> =
            kwargs.get_or(Qstr::MP_QSTR_verb, TR::buttons__confirm.into())?;
        let verb_cancel: Option<TString<'static>> = kwargs
            .get(Qstr::MP_QSTR_verb_cancel)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let reverse: bool = kwargs.get_or(Qstr::MP_QSTR_reverse, false)?;
        let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;

        let paragraphs = {
            let action = action.unwrap_or_default();
            let description = description.unwrap_or_default();
            let mut paragraphs = ParagraphVecShort::new();
            if !reverse {
                paragraphs
                    .add(Paragraph::new(&theme::TEXT_BOLD, action))
                    .add(Paragraph::new(&theme::TEXT_NORMAL, description));
            } else {
                paragraphs
                    .add(Paragraph::new(&theme::TEXT_NORMAL, description))
                    .add(Paragraph::new(&theme::TEXT_BOLD, action));
            }
            paragraphs.into_paragraphs()
        };

        content_in_button_page(title, paragraphs, verb, verb_cancel, hold)
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_blob(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let data: Obj = kwargs.get(Qstr::MP_QSTR_data)?;
        let description: Option<StrBuffer> =
            kwargs.get(Qstr::MP_QSTR_description)?.try_into_option()?;
        let extra: Option<StrBuffer> = kwargs.get(Qstr::MP_QSTR_extra)?.try_into_option()?;
        let verb: TString<'static> =
            kwargs.get_or(Qstr::MP_QSTR_verb, TR::buttons__confirm.into())?;
        let verb_cancel: Option<TString<'static>> = kwargs
            .get(Qstr::MP_QSTR_verb_cancel)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;
        let chunkify: bool = kwargs.get_or(Qstr::MP_QSTR_chunkify, false)?;

        let style = if chunkify {
            // Chunkifying the address into smaller pieces when requested
            &theme::TEXT_MONO_ADDRESS_CHUNKS
        } else {
            &theme::TEXT_MONO_DATA
        };

        let paragraphs = ConfirmBlob {
            description: description.unwrap_or_else(StrBuffer::empty),
            extra: extra.unwrap_or_else(StrBuffer::empty),
            data: data.try_into()?,
            description_font: &theme::TEXT_BOLD,
            extra_font: &theme::TEXT_NORMAL,
            data_font: style,
        }
        .into_paragraphs();

        content_in_button_page(title, paragraphs, verb, verb_cancel, hold)
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_properties(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;

        let mut paragraphs = ParagraphVecLong::new();

        for para in IterBuf::new().try_iterate(items)? {
            let [key, value, is_data]: [Obj; 3] = util::iter_into_array(para)?;
            let key = key.try_into_option::<StrBuffer>()?;
            let value = value.try_into_option::<StrBuffer>()?;
            let is_data: bool = is_data.try_into()?;

            if let Some(key) = key {
                if value.is_some() {
                    // Decreasing the margin between key and value (default is 5 px, we use 2 px)
                    // (this enables 4 lines - 2 key:value pairs - on the same screen)
                    paragraphs.add(
                        Paragraph::new(&theme::TEXT_BOLD, key)
                            .no_break()
                            .with_bottom_padding(2),
                    );
                } else {
                    paragraphs.add(Paragraph::new(&theme::TEXT_BOLD, key));
                }
            }
            if let Some(value) = value {
                let style = if is_data {
                    &theme::TEXT_MONO_DATA
                } else {
                    &theme::TEXT_MONO
                };
                paragraphs.add(Paragraph::new(style, value));
            }
        }

        content_in_button_page(
            title,
            paragraphs.into_paragraphs(),
            TR::buttons__confirm.into(),
            None,
            hold,
        )
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_homescreen(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let data: Obj = kwargs.get(Qstr::MP_QSTR_image)?;

        // Layout needs to hold the Obj to play nice with GC. Obj is resolved to &[u8]
        // in every paint pass.
        // SAFETY: We expect no existing mutable reference. Resulting reference is
        //         discarded before returning to micropython.
        let buffer_func = move || unsafe { unwrap!(get_buffer(data)) };

        let obj = LayoutObj::new(ConfirmHomescreen::new(title, buffer_func))?;
        Ok(obj.into())
    };

    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_reset_device(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let button: TString<'static> = kwargs.get(Qstr::MP_QSTR_button)?.try_into()?;

        let ops = OpTextLayout::<StrBuffer>::new(theme::TEXT_NORMAL)
            .text_normal(TR::reset__by_continuing.try_into()?)
            .next_page()
            .text_normal(TR::reset__more_info_at.try_into()?)
            .newline()
            .text_bold(TR::reset__tos_link.try_into()?);
        let formatted = FormattedText::new(ops).vertically_centered();

        content_in_button_page(title, formatted, button, Some("".into()), false)
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_backup(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], _kwargs: &Map| {
        // cached allocated translations that get_page can reuse
        let tr_title_success: StrBuffer = TR::words__title_success.try_into()?;
        let tr_new_wallet_created: StrBuffer = TR::backup__new_wallet_created.try_into()?;
        let tr_it_should_be_backed_up_now: StrBuffer =
            TR::backup__it_should_be_backed_up_now.try_into()?;
        let tr_title_backup_wallet: StrBuffer = TR::backup__title_backup_wallet.try_into()?;
        let tr_recover_anytime: StrBuffer = TR::backup__recover_anytime.try_into()?;

        let get_page = move |page_index| match page_index {
            0 => {
                let btn_layout = ButtonLayout::text_none_arrow_wide(TR::buttons__skip.into());
                let btn_actions = ButtonActions::cancel_none_next();
                let ops = OpTextLayout::new(theme::TEXT_NORMAL)
                    .text_normal(tr_new_wallet_created)
                    .newline()
                    .text_normal(tr_it_should_be_backed_up_now);
                let formatted = FormattedText::new(ops).vertically_centered();
                Page::new(btn_layout, btn_actions, formatted).with_title(tr_title_success)
            }
            1 => {
                let btn_layout = ButtonLayout::up_arrow_none_text(TR::buttons__back_up.into());
                let btn_actions = ButtonActions::prev_none_confirm();
                let ops = OpTextLayout::new(theme::TEXT_NORMAL).text_normal(tr_recover_anytime);
                let formatted = FormattedText::new(ops).vertically_centered();
                Page::<StrBuffer>::new(btn_layout, btn_actions, formatted)
                    .with_title(tr_title_backup_wallet)
            }
            _ => unreachable!(),
        };
        let pages = FlowPages::new(get_page, 2);

        let obj = LayoutObj::new(Flow::new(pages))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_address_details(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let address: StrBuffer = kwargs.get(Qstr::MP_QSTR_address)?.try_into()?;
        let case_sensitive: bool = kwargs.get(Qstr::MP_QSTR_case_sensitive)?.try_into()?;
        let account: Option<StrBuffer> = kwargs.get(Qstr::MP_QSTR_account)?.try_into_option()?;
        let path: Option<StrBuffer> = kwargs.get(Qstr::MP_QSTR_path)?.try_into_option()?;

        let xpubs: Obj = kwargs.get(Qstr::MP_QSTR_xpubs)?;

        let mut ad = AddressDetails::new(address, case_sensitive, account, path)?;

        for i in IterBuf::new().try_iterate(xpubs)? {
            let [xtitle, text]: [StrBuffer; 2] = util::iter_into_array(i)?;
            ad.add_xpub(xtitle, text)?;
        }

        let obj = LayoutObj::new(ad)?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_value(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: StrBuffer = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let value: StrBuffer = kwargs.get(Qstr::MP_QSTR_value)?.try_into()?;

        let verb: Option<TString<'static>> = kwargs
            .get(Qstr::MP_QSTR_verb)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;

        let paragraphs = Paragraphs::new([
            Paragraph::new(&theme::TEXT_BOLD, description),
            Paragraph::new(&theme::TEXT_MONO, value),
        ]);

        content_in_button_page(
            title,
            paragraphs,
            verb.unwrap_or(TR::buttons__confirm.into()),
            Some("".into()),
            hold,
        )
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_joint_total(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let spending_amount: StrBuffer = kwargs.get(Qstr::MP_QSTR_spending_amount)?.try_into()?;
        let total_amount: StrBuffer = kwargs.get(Qstr::MP_QSTR_total_amount)?.try_into()?;

        let paragraphs = Paragraphs::new([
            Paragraph::new(
                &theme::TEXT_BOLD,
                TR::joint__you_are_contributing.try_into()?,
            ),
            Paragraph::new(&theme::TEXT_MONO, spending_amount),
            Paragraph::new(
                &theme::TEXT_BOLD,
                TR::joint__to_the_total_amount.try_into()?,
            ),
            Paragraph::new(&theme::TEXT_MONO, total_amount),
        ]);

        content_in_button_page(
            TR::joint__title.try_into()?,
            paragraphs,
            TR::buttons__hold_to_confirm.into(),
            Some("".into()),
            true,
        )
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_modify_output(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let sign: i32 = kwargs.get(Qstr::MP_QSTR_sign)?.try_into()?;
        let amount_change: StrBuffer = kwargs.get(Qstr::MP_QSTR_amount_change)?.try_into()?;
        let amount_new: StrBuffer = kwargs.get(Qstr::MP_QSTR_amount_new)?.try_into()?;

        let description = if sign < 0 {
            TR::modify_amount__decrease_amount
        } else {
            TR::modify_amount__increase_amount
        };

        let paragraphs = Paragraphs::new([
            Paragraph::new(&theme::TEXT_NORMAL, description.try_into()?),
            Paragraph::new(&theme::TEXT_MONO, amount_change).break_after(),
            Paragraph::new(&theme::TEXT_BOLD, TR::modify_amount__new_amount.try_into()?),
            Paragraph::new(&theme::TEXT_MONO, amount_new),
        ]);

        content_in_button_page(
            TR::modify_amount__title.try_into()?,
            paragraphs,
            TR::buttons__confirm.into(),
            Some("".into()),
            false,
        )
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_output_address(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let address: StrBuffer = kwargs.get(Qstr::MP_QSTR_address)?.try_into()?;
        let address_label: StrBuffer = kwargs.get(Qstr::MP_QSTR_address_label)?.try_into()?;
        let address_title: StrBuffer = kwargs.get(Qstr::MP_QSTR_address_title)?.try_into()?;
        let chunkify: bool = kwargs.get_or(Qstr::MP_QSTR_chunkify, false)?;

        let get_page = move |page_index| {
            assert!(page_index == 0);
            // RECIPIENT + address
            let btn_layout = ButtonLayout::cancel_none_text(TR::buttons__continue.into());
            let btn_actions = ButtonActions::cancel_none_confirm();
            // Not putting hyphens in the address.
            // Potentially adding address label in different font.
            let mut ops = OpTextLayout::new(theme::TEXT_MONO_DATA);
            if !address_label.is_empty() {
                // NOTE: need to explicitly turn off the chunkification before rendering the
                // address label (for some reason it does not help to turn it off after
                // rendering the chunks)
                if chunkify {
                    ops = ops.chunkify_text(None);
                }
                ops = ops.text_normal(address_label).newline();
            }
            if chunkify {
                // Chunkifying the address into smaller pieces when requested
                ops = ops.chunkify_text(Some((theme::MONO_CHUNKS, 2)));
            }
            ops = ops.text_mono(address);
            let formatted = FormattedText::new(ops).vertically_centered();
            Page::new(btn_layout, btn_actions, formatted).with_title(address_title)
        };
        let pages = FlowPages::new(get_page, 1);

        let obj = LayoutObj::new(Flow::new(pages))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_output_amount(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let amount: StrBuffer = kwargs.get(Qstr::MP_QSTR_amount)?.try_into()?;
        let amount_title: StrBuffer = kwargs.get(Qstr::MP_QSTR_amount_title)?.try_into()?;

        let get_page = move |page_index| {
            assert!(page_index == 0);
            // AMOUNT + amount
            let btn_layout = ButtonLayout::up_arrow_none_text(TR::buttons__confirm.into());
            let btn_actions = ButtonActions::cancel_none_confirm();
            let ops = OpTextLayout::new(theme::TEXT_MONO).text_mono(amount);
            let formatted = FormattedText::new(ops).vertically_centered();
            Page::new(btn_layout, btn_actions, formatted).with_title(amount_title)
        };
        let pages = FlowPages::new(get_page, 1);

        let obj = LayoutObj::new(Flow::new(pages))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_total(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let total_amount: StrBuffer = kwargs.get(Qstr::MP_QSTR_total_amount)?.try_into()?;
        let fee_amount: StrBuffer = kwargs.get(Qstr::MP_QSTR_fee_amount)?.try_into()?;
        let fee_rate_amount: Option<StrBuffer> = kwargs
            .get(Qstr::MP_QSTR_fee_rate_amount)?
            .try_into_option()?;
        let account_label: Option<StrBuffer> =
            kwargs.get(Qstr::MP_QSTR_account_label)?.try_into_option()?;
        let total_label: StrBuffer = kwargs.get(Qstr::MP_QSTR_total_label)?.try_into()?;
        let fee_label: StrBuffer = kwargs.get(Qstr::MP_QSTR_fee_label)?.try_into()?;

        // cached allocated translated strings that get_page can reuse
        let tr_title_fee = TR::confirm_total__title_fee.try_into()?;
        let tr_fee_rate = TR::confirm_total__fee_rate.try_into()?;
        let tr_title_sending_from = TR::confirm_total__title_sending_from.try_into()?;
        let tr_account = TR::words__account_colon.try_into()?;

        let get_page = move |page_index| {
            match page_index {
                0 => {
                    // Total amount + fee
                    let btn_layout = ButtonLayout::cancel_armed_info(TR::buttons__confirm.into());
                    let btn_actions = ButtonActions::cancel_confirm_next();

                    let ops = OpTextLayout::new(theme::TEXT_MONO)
                        .text_bold(total_label)
                        .newline()
                        .text_mono(total_amount)
                        .newline()
                        .newline()
                        .text_bold(fee_label)
                        .newline()
                        .text_mono(fee_amount);

                    let formatted = FormattedText::new(ops);
                    Page::new(btn_layout, btn_actions, formatted)
                }
                1 => {
                    // Fee rate info
                    let btn_layout = ButtonLayout::arrow_none_arrow();
                    let btn_actions = ButtonActions::prev_none_next();

                    let fee_rate_amount = fee_rate_amount.unwrap_or_default();

                    let ops = OpTextLayout::new(theme::TEXT_MONO)
                        .text_bold(tr_title_fee)
                        .newline()
                        .newline()
                        .newline_half()
                        .text_bold(tr_fee_rate)
                        .newline()
                        .text_mono(fee_rate_amount);

                    let formatted = FormattedText::new(ops);
                    Page::new(btn_layout, btn_actions, formatted)
                }
                2 => {
                    // Wallet and account info
                    let btn_layout = ButtonLayout::arrow_none_none();
                    let btn_actions = ButtonActions::prev_none_none();

                    let account_label = account_label.unwrap_or_default();

                    // TODO: include wallet info when available

                    let ops = OpTextLayout::new(theme::TEXT_MONO)
                        .text_bold(tr_title_sending_from)
                        .newline()
                        .newline()
                        .newline_half()
                        .text_bold(tr_account)
                        .newline()
                        .text_mono(account_label);

                    let formatted = FormattedText::new(ops);
                    Page::new(btn_layout, btn_actions, formatted)
                }
                _ => unreachable!(),
            }
        };
        let pages = FlowPages::new(get_page, 3);

        let obj = LayoutObj::new(Flow::new(pages))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_altcoin_tx_summary(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let amount_title: StrBuffer = kwargs.get(Qstr::MP_QSTR_amount_title)?.try_into()?;
        let amount_value: StrBuffer = kwargs.get(Qstr::MP_QSTR_amount_value)?.try_into()?;
        let fee_title: StrBuffer = kwargs.get(Qstr::MP_QSTR_fee_title)?.try_into()?;
        let fee_value: StrBuffer = kwargs.get(Qstr::MP_QSTR_fee_value)?.try_into()?;
        let cancel_cross: bool = kwargs.get_or(Qstr::MP_QSTR_cancel_cross, false)?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;

        // cached allocated translated strings that get_page can reuse
        let tr_title_fee = TR::confirm_total__title_fee.try_into()?;

        let get_page = move |page_index| {
            match page_index {
                0 => {
                    // Amount + fee
                    let btn_layout = if cancel_cross {
                        ButtonLayout::cancel_armed_info(TR::buttons__confirm.into())
                    } else {
                        ButtonLayout::up_arrow_armed_info(TR::buttons__confirm.into())
                    };
                    let btn_actions = ButtonActions::cancel_confirm_next();

                    let ops = OpTextLayout::new(theme::TEXT_MONO)
                        .text_mono(amount_value)
                        .newline()
                        .newline_half()
                        .text_bold(fee_title)
                        .newline()
                        .text_mono(fee_value);

                    let formatted = FormattedText::new(ops);
                    Page::new(btn_layout, btn_actions, formatted).with_title(amount_title)
                }
                1 => {
                    // Other information
                    let btn_layout = ButtonLayout::arrow_none_none();
                    let btn_actions = ButtonActions::prev_none_none();

                    let mut ops = OpTextLayout::new(theme::TEXT_MONO);

                    for item in unwrap!(IterBuf::new().try_iterate(items)) {
                        let [key, value]: [Obj; 2] = unwrap!(util::iter_into_array(item));
                        if !ops.is_empty() {
                            // Each key-value pair is on its own page
                            ops = ops.next_page();
                        }
                        ops = ops
                            .text_bold(unwrap!(key.try_into()))
                            .newline()
                            .text_mono(unwrap!(value.try_into()));
                    }

                    let formatted = FormattedText::new(ops).vertically_centered();
                    Page::new(btn_layout, btn_actions, formatted)
                        .with_title(tr_title_fee)
                        .with_slim_arrows()
                }
                _ => unreachable!(),
            }
        };
        let pages = FlowPages::new(get_page, 2);

        let obj = LayoutObj::new(Flow::new(pages).with_scrollbar(false))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_address(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let address: StrBuffer = kwargs.get(Qstr::MP_QSTR_data)?.try_into()?;
        let verb: TString<'static> =
            kwargs.get_or(Qstr::MP_QSTR_verb, TR::buttons__confirm.into())?;
        let chunkify: bool = kwargs.get_or(Qstr::MP_QSTR_chunkify, false)?;

        let get_page = move |page_index| {
            assert!(page_index == 0);

            let btn_layout = ButtonLayout::cancel_armed_info(verb);
            let btn_actions = ButtonActions::cancel_confirm_info();
            let style = if chunkify {
                // Chunkifying the address into smaller pieces when requested
                theme::TEXT_MONO_ADDRESS_CHUNKS
            } else {
                theme::TEXT_MONO_DATA
            };
            let ops = OpTextLayout::new(style).text_mono(address);
            let formatted = FormattedText::new(ops).vertically_centered();
            Page::new(btn_layout, btn_actions, formatted).with_title(title)
        };
        let pages = FlowPages::new(get_page, 1);

        let obj = LayoutObj::new(Flow::new(pages))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

/// General pattern of most tutorial screens.
/// (title, text, btn_layout, btn_actions, text_y_offset)
fn tutorial_screen(
    title: StrBuffer,
    text: StrBuffer,
    btn_layout: ButtonLayout,
    btn_actions: ButtonActions,
) -> Page<StrBuffer> {
    let ops = OpTextLayout::<StrBuffer>::new(theme::TEXT_NORMAL).text_normal(text);
    let formatted = FormattedText::new(ops).vertically_centered();
    Page::new(btn_layout, btn_actions, formatted).with_title(title)
}

extern "C" fn tutorial(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], _kwargs: &Map| {
        const PAGE_COUNT: usize = 7;

        // cached allocated translated strings that get_page can reuse
        let tr_title_hello: StrBuffer = TR::tutorial__title_hello.try_into()?;
        let tr_welcome_press_right: StrBuffer = TR::tutorial__welcome_press_right.try_into()?;
        let tr_use_trezor: StrBuffer = TR::tutorial__use_trezor.try_into()?;
        let tr_hold_to_confirm: StrBuffer = TR::buttons__hold_to_confirm.try_into()?;
        let tr_press_and_hold: StrBuffer = TR::tutorial__press_and_hold.try_into()?;
        let tr_title_screen_scroll: StrBuffer = TR::tutorial__title_screen_scroll.try_into()?;
        let tr_scroll_down: StrBuffer = TR::tutorial__scroll_down.try_into()?;
        let tr_confirm: StrBuffer = TR::buttons__confirm.try_into()?;
        let tr_middle_click: StrBuffer = TR::tutorial__middle_click.try_into()?;
        let tr_title_tutorial_complete: StrBuffer =
            TR::tutorial__title_tutorial_complete.try_into()?;
        let tr_ready_to_use: StrBuffer = TR::tutorial__ready_to_use.try_into()?;
        let tr_title_skip: StrBuffer = TR::tutorial__title_skip.try_into()?;
        let tr_sure_you_want_skip: StrBuffer = TR::tutorial__sure_you_want_skip.try_into()?;

        let get_page = move |page_index| {
            // Lazy-loaded list of screens to show, with custom content,
            // buttons and actions triggered by these buttons.
            // Cancelling the first screen will point to the last one,
            // which asks for confirmation whether user wants to
            // really cancel the tutorial.
            match page_index {
                // title, text, btn_layout, btn_actions
                0 => tutorial_screen(
                    tr_title_hello,
                    tr_welcome_press_right,
                    ButtonLayout::cancel_none_arrow(),
                    ButtonActions::last_none_next(),
                ),
                1 => tutorial_screen(
                    "".into(),
                    tr_use_trezor,
                    ButtonLayout::arrow_none_arrow(),
                    ButtonActions::prev_none_next(),
                ),
                2 => tutorial_screen(
                    tr_hold_to_confirm,
                    tr_press_and_hold,
                    ButtonLayout::arrow_none_htc(TR::buttons__hold_to_confirm.into()),
                    ButtonActions::prev_none_next(),
                ),
                3 => tutorial_screen(
                    tr_title_screen_scroll,
                    tr_scroll_down,
                    ButtonLayout::arrow_none_text(TR::buttons__continue.into()),
                    ButtonActions::prev_none_next(),
                ),
                4 => tutorial_screen(
                    tr_confirm,
                    tr_middle_click,
                    ButtonLayout::none_armed_none(TR::buttons__confirm.into()),
                    ButtonActions::none_next_none(),
                ),
                5 => tutorial_screen(
                    tr_title_tutorial_complete,
                    tr_ready_to_use,
                    ButtonLayout::text_none_text(
                        TR::buttons__again.into(),
                        TR::buttons__continue.into(),
                    ),
                    ButtonActions::beginning_none_confirm(),
                ),
                6 => tutorial_screen(
                    tr_title_skip,
                    tr_sure_you_want_skip,
                    ButtonLayout::arrow_none_text(TR::buttons__skip.into()),
                    ButtonActions::beginning_none_cancel(),
                ),
                _ => unreachable!(),
            }
        };

        let pages = FlowPages::new(get_page, PAGE_COUNT);

        // Setting the ignore-second-button to mimic all the Choice pages, to teach user
        // that they should really press both buttons at the same time to achieve
        // middle-click.
        let obj = LayoutObj::new(
            Flow::new(pages)
                .with_scrollbar(false)
                .with_ignore_second_button_ms(constant::IGNORE_OTHER_BTN_MS),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_modify_fee(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let sign: i32 = kwargs.get(Qstr::MP_QSTR_sign)?.try_into()?;
        let user_fee_change: StrBuffer = kwargs.get(Qstr::MP_QSTR_user_fee_change)?.try_into()?;
        let total_fee_new: StrBuffer = kwargs.get(Qstr::MP_QSTR_total_fee_new)?.try_into()?;
        let fee_rate_amount: Option<StrBuffer> = kwargs
            .get(Qstr::MP_QSTR_fee_rate_amount)?
            .try_into_option()?;

        let (description, change) = match sign {
            s if s < 0 => (TR::modify_fee__decrease_fee, user_fee_change),
            s if s > 0 => (TR::modify_fee__increase_fee, user_fee_change),
            _ => (TR::modify_fee__no_change, StrBuffer::empty()),
        };

        let mut paragraphs_vec = ParagraphVecShort::new();
        paragraphs_vec
            .add(Paragraph::new(&theme::TEXT_BOLD, description.try_into()?))
            .add(Paragraph::new(&theme::TEXT_MONO, change))
            .add(
                Paragraph::new(
                    &theme::TEXT_BOLD,
                    TR::modify_fee__transaction_fee.try_into()?,
                )
                .no_break(),
            )
            .add(Paragraph::new(&theme::TEXT_MONO, total_fee_new));

        if let Some(fee_rate_amount) = fee_rate_amount {
            paragraphs_vec
                .add(
                    Paragraph::new(&theme::TEXT_BOLD, TR::modify_fee__fee_rate.try_into()?)
                        .no_break(),
                )
                .add(Paragraph::new(&theme::TEXT_MONO, fee_rate_amount));
        }

        content_in_button_page(
            TR::modify_fee__title.try_into()?,
            paragraphs_vec.into_paragraphs(),
            TR::buttons__confirm.into(),
            Some("".into()),
            false,
        )
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_multiple_pages_texts(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let verb: TString<'static> = kwargs.get(Qstr::MP_QSTR_verb)?.try_into()?;
        let items: Gc<List> = kwargs.get(Qstr::MP_QSTR_items)?.try_into()?;

        // Cache the page count so that we can move `items` into the closure.
        let page_count = items.len();

        // Closure to lazy-load the information on given page index.
        // Done like this to allow arbitrarily many pages without
        // the need of any allocation here in Rust.
        let get_page = move |page_index| {
            let item_obj = unwrap!(items.get(page_index));
            let text = unwrap!(item_obj.try_into());

            let (btn_layout, btn_actions) = if page_count == 1 {
                // There is only one page
                (
                    ButtonLayout::cancel_none_text(verb),
                    ButtonActions::cancel_none_confirm(),
                )
            } else if page_index == 0 {
                // First page
                (
                    ButtonLayout::cancel_none_arrow_wide(),
                    ButtonActions::cancel_none_next(),
                )
            } else if page_index == page_count - 1 {
                // Last page
                (
                    ButtonLayout::up_arrow_none_text(verb),
                    ButtonActions::prev_none_confirm(),
                )
            } else {
                // Page in the middle
                (
                    ButtonLayout::up_arrow_none_arrow_wide(),
                    ButtonActions::prev_none_next(),
                )
            };

            let ops = OpTextLayout::new(theme::TEXT_NORMAL).text_normal(text);
            let formatted = FormattedText::new(ops).vertically_centered();

            Page::new(btn_layout, btn_actions, formatted)
        };

        let pages = FlowPages::new(get_page, page_count);
        let obj = LayoutObj::new(Flow::new(pages).with_common_title(title))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_fido(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let app_name: StrBuffer = kwargs.get(Qstr::MP_QSTR_app_name)?.try_into()?;
        let accounts: Gc<List> = kwargs.get(Qstr::MP_QSTR_accounts)?.try_into()?;

        // Cache the page count so that we can move `accounts` into the closure.
        let page_count = accounts.len();

        // Closure to lazy-load the information on given page index.
        // Done like this to allow arbitrarily many pages without
        // the need of any allocation here in Rust.
        let get_page = move |page_index| {
            let account_obj = unwrap!(accounts.get(page_index));
            let account = account_obj.try_into().unwrap_or_else(|_| "".into());

            let (btn_layout, btn_actions) = if page_count == 1 {
                // There is only one page
                (
                    ButtonLayout::cancel_none_text(TR::buttons__confirm.into()),
                    ButtonActions::cancel_none_confirm(),
                )
            } else if page_index == 0 {
                // First page
                (
                    ButtonLayout::cancel_armed_arrow(TR::buttons__select.into()),
                    ButtonActions::cancel_confirm_next(),
                )
            } else if page_index == page_count - 1 {
                // Last page
                (
                    ButtonLayout::arrow_armed_none(TR::buttons__select.into()),
                    ButtonActions::prev_confirm_none(),
                )
            } else {
                // Page in the middle
                (
                    ButtonLayout::arrow_armed_arrow(TR::buttons__select.into()),
                    ButtonActions::prev_confirm_next(),
                )
            };

            let ops = OpTextLayout::new(theme::TEXT_NORMAL)
                .newline()
                .text_normal(app_name)
                .newline()
                .text_bold(account);
            let formatted = FormattedText::new(ops);

            Page::new(btn_layout, btn_actions, formatted)
        };

        let pages = FlowPages::new(get_page, page_count);
        // Returning the page index in case of confirmation.
        let obj = LayoutObj::new(
            Flow::new(pages)
                .with_common_title(title)
                .with_return_confirmed_index(),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_warning(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let button: TString<'static> = kwargs.get(Qstr::MP_QSTR_button)?.try_into()?;
        let warning: StrBuffer = kwargs.get(Qstr::MP_QSTR_warning)?.try_into()?;
        let description: StrBuffer = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;

        let get_page = move |page_index| {
            assert!(page_index == 0);

            let btn_layout = ButtonLayout::none_armed_none(button);
            let btn_actions = ButtonActions::none_confirm_none();
            let mut ops = OpTextLayout::<StrBuffer>::new(theme::TEXT_NORMAL);
            ops = ops.alignment(geometry::Alignment::Center);
            if !warning.is_empty() {
                ops = ops.text_bold(warning).newline();
            }
            if !description.is_empty() {
                ops = ops.text_normal(description);
            }
            let formatted = FormattedText::new(ops).vertically_centered();
            Page::new(btn_layout, btn_actions, formatted)
        };
        let pages = FlowPages::new(get_page, 1);
        let obj = LayoutObj::new(Flow::new(pages))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_info(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: StrBuffer =
            kwargs.get_or(Qstr::MP_QSTR_description, StrBuffer::empty())?;
        let time_ms: u32 = kwargs.get_or(Qstr::MP_QSTR_time_ms, 0)?;

        let content = Frame::new(
            title,
            Paragraphs::new([Paragraph::new(&theme::TEXT_NORMAL, description)]),
        );
        let obj = if time_ms == 0 {
            // No timer, used when we only want to draw the dialog once and
            // then throw away the layout object.
            LayoutObj::new(content)?
        } else {
            // Timeout.
            let timeout = Timeout::new(time_ms);
            LayoutObj::new((timeout, content.map(|_| None)))?
        };

        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_passphrase() -> Obj {
    let block = move || {
        let text: StrBuffer = TR::passphrase__please_enter.try_into()?;
        let paragraph = Paragraph::new(&theme::TEXT_NORMAL, text).centered();
        let content = Paragraphs::new([paragraph]);
        let obj = LayoutObj::new(content)?;
        Ok(obj.into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn new_show_waiting_text(message: Obj) -> Obj {
    let block = || {
        let text: StrBuffer = message.try_into()?;
        let paragraph = Paragraph::new(&theme::TEXT_NORMAL, text).centered();
        let content = Paragraphs::new([paragraph]);
        let obj = LayoutObj::new(content)?;
        Ok(obj.into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn new_show_mismatch(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;

        // cached allocated translated strings that get_page can reuse
        let tr_contact_support_at = TR::addr_mismatch__contact_support_at.try_into()?;
        let tr_support_url = TR::addr_mismatch__support_url.try_into()?;

        let get_page = move |page_index| {
            assert!(page_index == 0);

            let btn_layout = ButtonLayout::arrow_none_text(TR::buttons__quit.into());
            let btn_actions = ButtonActions::cancel_none_confirm();
            let ops = OpTextLayout::<StrBuffer>::new(theme::TEXT_NORMAL)
                .text_bold(title)
                .newline()
                .newline_half()
                .text_normal(tr_contact_support_at)
                .newline()
                .text_bold(tr_support_url);
            let formatted = FormattedText::new(ops);
            Page::new(btn_layout, btn_actions, formatted)
        };
        let pages = FlowPages::new(get_page, 1);

        let obj = LayoutObj::new(Flow::new(pages))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_with_info(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let button: TString<'static> = kwargs.get(Qstr::MP_QSTR_button)?.try_into()?;
        let verb_cancel: Option<TString<'static>> = kwargs
            .get(Qstr::MP_QSTR_verb_cancel)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;

        let mut paragraphs = ParagraphVecShort::new();

        for para in IterBuf::new().try_iterate(items)? {
            let [font, text]: [Obj; 2] = util::iter_into_array(para)?;
            let style: &TextStyle = theme::textstyle_number(font.try_into()?);
            let text: StrBuffer = text.try_into()?;
            paragraphs.add(Paragraph::new(style, text));
            if paragraphs.is_full() {
                break;
            }
        }

        let obj = LayoutObj::new(Frame::new(
            title,
            ShowMore::<Paragraphs<ParagraphVecShort<StrBuffer>>>::new(
                paragraphs.into_paragraphs(),
                verb_cancel,
                button,
            ),
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_more(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let button: TString<'static> = kwargs.get(Qstr::MP_QSTR_button)?.try_into()?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;

        let mut paragraphs = ParagraphVecLong::new();

        for para in IterBuf::new().try_iterate(items)? {
            let [font, text]: [Obj; 2] = util::iter_into_array(para)?;
            let style: &TextStyle = theme::textstyle_number(font.try_into()?);
            let text: StrBuffer = text.try_into()?;
            paragraphs.add(Paragraph::new(style, text));
        }

        content_in_button_page(
            title,
            paragraphs.into_paragraphs(),
            button,
            Some("<".into()),
            false,
        )
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_coinjoin(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let max_rounds: StrBuffer = kwargs.get(Qstr::MP_QSTR_max_rounds)?.try_into()?;
        let max_feerate: StrBuffer = kwargs.get(Qstr::MP_QSTR_max_feerate)?.try_into()?;

        // Decreasing bottom padding between paragraphs to fit one screen
        let paragraphs = Paragraphs::new([
            Paragraph::new(&theme::TEXT_BOLD, TR::coinjoin__max_rounds.try_into()?)
                .with_bottom_padding(2),
            Paragraph::new(&theme::TEXT_MONO, max_rounds),
            Paragraph::new(&theme::TEXT_BOLD, TR::coinjoin__max_mining_fee.try_into()?)
                .with_bottom_padding(2)
                .no_break(),
            Paragraph::new(&theme::TEXT_MONO, max_feerate).with_bottom_padding(2),
        ]);

        content_in_button_page(
            TR::coinjoin__title.try_into()?,
            paragraphs,
            TR::buttons__hold_to_confirm.into(),
            None,
            true,
        )
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_pin(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let prompt: StrBuffer = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let subprompt: StrBuffer = kwargs.get(Qstr::MP_QSTR_subprompt)?.try_into()?;

        let obj = LayoutObj::new(PinEntry::new(prompt, subprompt))?;

        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_passphrase(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let prompt: StrBuffer = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;

        let obj = LayoutObj::new(Frame::new(prompt, PassphraseEntry::new()).with_title_centered())?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_bip39(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let prompt: StrBuffer = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let prefill_word: StrBuffer = kwargs.get(Qstr::MP_QSTR_prefill_word)?.try_into()?;
        let can_go_back: bool = kwargs.get(Qstr::MP_QSTR_can_go_back)?.try_into()?;

        let obj = LayoutObj::new(
            Frame::new(
                prompt,
                WordlistEntry::prefilled_word(
                    prefill_word.as_ref(),
                    WordlistType::Bip39,
                    can_go_back,
                ),
            )
            .with_title_centered(),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_slip39(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let prompt: StrBuffer = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let prefill_word: StrBuffer = kwargs.get(Qstr::MP_QSTR_prefill_word)?.try_into()?;
        let can_go_back: bool = kwargs.get(Qstr::MP_QSTR_can_go_back)?.try_into()?;

        let obj = LayoutObj::new(
            Frame::new(
                prompt,
                WordlistEntry::prefilled_word(
                    prefill_word.as_ref(),
                    WordlistType::Slip39,
                    can_go_back,
                ),
            )
            .with_title_centered(),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_select_word(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        // we ignore passed in `title` and use `description` in its place
        let description: StrBuffer = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let words_iterable: Obj = kwargs.get(Qstr::MP_QSTR_words)?;
        // There are only 3 words, but SimpleChoice requires 5 elements
        let words: Vec<TString<'static>, 5> = util::iter_into_vec(words_iterable)?;

        // Returning the index of the selected word, not the word itself
        let obj = LayoutObj::new(
            Frame::new(
                description,
                SimpleChoice::new(words, false)
                    .with_show_incomplete()
                    .with_return_index(),
            )
            .with_title_centered(),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_share_words(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let share_words_obj: Obj = kwargs.get(Qstr::MP_QSTR_share_words)?;
        let share_words: Vec<StrBuffer, 33> = util::iter_into_vec(share_words_obj)?;

        let cancel_btn = Some(ButtonDetails::up_arrow_icon());
        let confirm_btn =
            Some(ButtonDetails::text(TR::buttons__hold_to_confirm.into()).with_default_duration());

        let obj = LayoutObj::new(
            ButtonPage::new(ShareWords::new(share_words), theme::BG)
                .with_cancel_btn(cancel_btn)
                .with_confirm_btn(confirm_btn),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_number(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let min_count: u32 = kwargs.get(Qstr::MP_QSTR_min_count)?.try_into()?;
        let max_count: u32 = kwargs.get(Qstr::MP_QSTR_max_count)?.try_into()?;
        let count: u32 = kwargs.get(Qstr::MP_QSTR_count)?.try_into()?;

        let obj = LayoutObj::new(
            Frame::new(title, NumberInput::new(min_count, max_count, count)).with_title_centered(),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_checklist(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let button: TString<'static> = kwargs.get(Qstr::MP_QSTR_button)?.try_into()?;
        let active: usize = kwargs.get(Qstr::MP_QSTR_active)?.try_into()?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;

        let mut paragraphs = ParagraphVecLong::new();
        for (i, item) in IterBuf::new().try_iterate(items)?.enumerate() {
            let style = match i.cmp(&active) {
                Ordering::Less => &theme::TEXT_NORMAL,
                Ordering::Equal => &theme::TEXT_BOLD,
                Ordering::Greater => &theme::TEXT_NORMAL,
            };
            let text: StrBuffer = item.try_into()?;
            paragraphs.add(Paragraph::new(style, text));
        }

        let confirm_btn = Some(ButtonDetails::text(button));

        let obj = LayoutObj::new(
            ButtonPage::new(
                Checklist::from_paragraphs(
                    theme::ICON_ARROW_RIGHT_FAT,
                    theme::ICON_TICK_FAT,
                    active,
                    paragraphs
                        .into_paragraphs()
                        .with_spacing(theme::CHECKLIST_SPACING),
                )
                .with_check_width(theme::CHECKLIST_CHECK_WIDTH)
                .with_current_offset(theme::CHECKLIST_CURRENT_OFFSET),
                theme::BG,
            )
            .with_confirm_btn(confirm_btn),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_recovery(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let description: StrBuffer = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let button: TString<'static> = kwargs.get(Qstr::MP_QSTR_button)?.try_into()?;
        let dry_run: bool = kwargs.get(Qstr::MP_QSTR_dry_run)?.try_into()?;
        let show_info: bool = kwargs.get(Qstr::MP_QSTR_show_info)?.try_into()?;

        let mut paragraphs = ParagraphVecShort::new();
        paragraphs.add(Paragraph::new(&theme::TEXT_NORMAL, description));
        if show_info {
            paragraphs
                .add(Paragraph::new(
                    &theme::TEXT_NORMAL,
                    TR::recovery__only_first_n_letters.try_into()?,
                ))
                .add(Paragraph::new(
                    &theme::TEXT_NORMAL,
                    TR::recovery__cursor_will_change.try_into()?,
                ));
        }

        let title = if dry_run {
            TR::recovery__title_dry_run
        } else {
            TR::recovery__title
        };

        content_in_button_page(
            title.try_into()?,
            paragraphs.into_paragraphs(),
            button,
            Some("".into()),
            false,
        )
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_select_word_count(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], _kwargs: &Map| {
        let title: StrBuffer = TR::word_count__title.try_into()?;

        let choices: Vec<TString<'static>, 5> = ["12", "18", "20", "24", "33"]
            .map(|num| num.into())
            .into_iter()
            .collect();

        let obj = LayoutObj::new(
            Frame::new(title, SimpleChoice::new(choices, false)).with_title_centered(),
        )?;
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
        let lines: [StrBuffer; 4] = util::iter_into_array(lines_iterable)?;

        let [l0, l1, l2, l3] = lines;

        let paragraphs = Paragraphs::new([
            Paragraph::new(&theme::TEXT_MONO, l0),
            Paragraph::new(&theme::TEXT_BOLD, l1),
            Paragraph::new(&theme::TEXT_MONO, l2),
            Paragraph::new(&theme::TEXT_BOLD, l3),
        ]);

        content_in_button_page(
            "".into(),
            paragraphs,
            TR::buttons__continue.into(),
            None,
            false,
        )
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_progress(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let indeterminate: bool = kwargs.get_or(Qstr::MP_QSTR_indeterminate, false)?;
        let description: StrBuffer =
            kwargs.get_or(Qstr::MP_QSTR_description, StrBuffer::empty())?;

        // Description updates are received as &str and we need to provide a way to
        // convert them to StrBuffer.
        let obj = LayoutObj::new(
            Progress::new(indeterminate, description)
                .with_title(title)
                .with_update_description(StrBuffer::alloc),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_progress_coinjoin(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let indeterminate: bool = kwargs.get_or(Qstr::MP_QSTR_indeterminate, false)?;
        let time_ms: u32 = kwargs.get_or(Qstr::MP_QSTR_time_ms, 0)?;
        let skip_first_paint: bool = kwargs.get_or(Qstr::MP_QSTR_skip_first_paint, false)?;

        // The second type parameter is actually not used in `new()` but we need to
        // provide it.
        let progress = CoinJoinProgress::new(title, indeterminate);
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
        let label: StrBuffer = kwargs
            .get(Qstr::MP_QSTR_label)?
            .try_into_option()?
            .unwrap_or_else(|| model::FULL_NAME.into());
        let notification: Option<StrBuffer> =
            kwargs.get(Qstr::MP_QSTR_notification)?.try_into_option()?;
        let notification_level: u8 = kwargs.get_or(Qstr::MP_QSTR_notification_level, 0)?;
        let skip_first_paint: bool = kwargs.get(Qstr::MP_QSTR_skip_first_paint)?.try_into()?;
        let hold: bool = kwargs.get(Qstr::MP_QSTR_hold)?.try_into()?;

        let notification = notification.map(|w| (w, notification_level));
        let loader_description = hold.then_some("Locking the device...".into());
        let obj = LayoutObj::new(Homescreen::new(label, notification, loader_description))?;
        if skip_first_paint {
            obj.skip_first_paint();
        }
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_lockscreen(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let label: StrBuffer = kwargs
            .get(Qstr::MP_QSTR_label)?
            .try_into_option()?
            .unwrap_or_else(|| model::FULL_NAME.into());
        let bootscreen: bool = kwargs.get(Qstr::MP_QSTR_bootscreen)?.try_into()?;
        let coinjoin_authorized: bool = kwargs.get_or(Qstr::MP_QSTR_coinjoin_authorized, false)?;
        let skip_first_paint: bool = kwargs.get(Qstr::MP_QSTR_skip_first_paint)?.try_into()?;

        let obj = LayoutObj::new(Lockscreen::new(label, bootscreen, coinjoin_authorized)?)?;
        if skip_first_paint {
            obj.skip_first_paint();
        }
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_firmware_update(
    n_args: usize,
    args: *const Obj,
    kwargs: *mut Map,
) -> Obj {
    use super::component::bl_confirm::Confirm;
    let block = move |_args: &[Obj], kwargs: &Map| {
        let description: StrBuffer = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let fingerprint: StrBuffer = kwargs.get(Qstr::MP_QSTR_fingerprint)?.try_into()?;

        let title = TR::firmware_update__title;
        let message = Label::left_aligned(description, theme::TEXT_NORMAL).vertically_centered();
        let fingerprint = Label::left_aligned(
            fingerprint,
            theme::TEXT_NORMAL.with_line_breaking(LineBreaking::BreakWordsNoHyphen),
        )
        .vertically_centered();

        let obj = LayoutObj::new(
            Confirm::new(theme::BG, title, message, None, TR::buttons__install, false)
                .with_info_screen(TR::firmware_update__title_fingerprint, fingerprint),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

pub extern "C" fn upy_check_homescreen_format(data: Obj) -> Obj {
    let block = || {
        // SAFETY: buffer does not outlive this function
        let buffer = unsafe { get_buffer(data) }?;

        Ok(display::toif::Toif::new(buffer)
            .map(|toif| check_homescreen_format(&toif))
            .unwrap_or(false)
            .into())
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn new_show_wait_text(message: Obj) -> Obj {
    let block = || {
        let message: TString<'static> = message.try_into()?;
        let obj = LayoutObj::new(Connect::new(message, theme::FG, theme::BG))?;
        Ok(obj.into())
    };

    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
pub static mp_module_trezorui2: Module = obj_module! {
    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezorui2.to_obj(),

    /// CONFIRMED: object
    Qstr::MP_QSTR_CONFIRMED => CONFIRMED.as_obj(),

    /// CANCELLED: object
    Qstr::MP_QSTR_CANCELLED => CANCELLED.as_obj(),

    /// INFO: object
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
    ///     verb: str = "CONFIRM",
    ///     verb_cancel: str | None = None,
    ///     hold: bool = False,
    ///     hold_danger: bool = False,  # unused on TR
    ///     reverse: bool = False,
    /// ) -> object:
    ///     """Confirm action."""
    Qstr::MP_QSTR_confirm_action => obj_fn_kw!(0, new_confirm_action).as_obj(),

    /// def confirm_homescreen(
    ///     *,
    ///     title: str,
    ///     image: bytes,
    /// ) -> object:
    ///     """Confirm homescreen."""
    Qstr::MP_QSTR_confirm_homescreen => obj_fn_kw!(0, new_confirm_homescreen).as_obj(),

    /// def confirm_blob(
    ///     *,
    ///     title: str,
    ///     data: str | bytes,
    ///     description: str | None,
    ///     extra: str | None,
    ///     verb: str = "CONFIRM",
    ///     verb_cancel: str | None = None,
    ///     hold: bool = False,
    ///     chunkify: bool = False,
    /// ) -> object:
    ///     """Confirm byte sequence data."""
    Qstr::MP_QSTR_confirm_blob => obj_fn_kw!(0, new_confirm_blob).as_obj(),

    /// def confirm_address(
    ///     *,
    ///     title: str,
    ///     data: str,
    ///     description: str | None,  # unused on TR
    ///     extra: str | None,  # unused on TR
    ///     verb: str = "CONFIRM",
    ///     chunkify: bool = False,
    /// ) -> object:
    ///     """Confirm address."""
    Qstr::MP_QSTR_confirm_address => obj_fn_kw!(0, new_confirm_address).as_obj(),


    /// def confirm_properties(
    ///     *,
    ///     title: str,
    ///     items: list[tuple[str | None, str | bytes | None, bool]],
    ///     hold: bool = False,
    /// ) -> object:
    ///     """Confirm list of key-value pairs. The third component in the tuple should be True if
    ///     the value is to be rendered as binary with monospace font, False otherwise.
    ///     This only concerns the text style, you need to decode the value to UTF-8 in python."""
    Qstr::MP_QSTR_confirm_properties => obj_fn_kw!(0, new_confirm_properties).as_obj(),

    /// def confirm_reset_device(
    ///     *,
    ///     title: str,
    ///     button: str,
    /// ) -> object:
    ///     """Confirm TOS before device setup."""
    Qstr::MP_QSTR_confirm_reset_device => obj_fn_kw!(0, new_confirm_reset_device).as_obj(),

    /// def confirm_backup() -> object:
    ///     """Strongly recommend user to do backup."""
    Qstr::MP_QSTR_confirm_backup => obj_fn_kw!(0, new_confirm_backup).as_obj(),

    /// def show_address_details(
    ///     *,
    ///     address: str,
    ///     case_sensitive: bool,
    ///     account: str | None,
    ///     path: str | None,
    ///     xpubs: list[tuple[str, str]],
    /// ) -> object:
    ///     """Show address details - QR code, account, path, cosigner xpubs."""
    Qstr::MP_QSTR_show_address_details => obj_fn_kw!(0, new_show_address_details).as_obj(),

    /// def confirm_value(
    ///     *,
    ///     title: str,
    ///     description: str,
    ///     value: str,
    ///     verb: str | None = None,
    ///     hold: bool = False,
    /// ) -> object:
    ///     """Confirm value."""
    Qstr::MP_QSTR_confirm_value => obj_fn_kw!(0, new_confirm_value).as_obj(),

    /// def confirm_joint_total(
    ///     *,
    ///     spending_amount: str,
    ///     total_amount: str,
    /// ) -> object:
    ///     """Confirm total if there are external inputs."""
    Qstr::MP_QSTR_confirm_joint_total => obj_fn_kw!(0, new_confirm_joint_total).as_obj(),

    /// def confirm_modify_output(
    ///     *,
    ///     sign: int,
    ///     amount_change: str,
    ///     amount_new: str,
    /// ) -> object:
    ///     """Decrease or increase output amount."""
    Qstr::MP_QSTR_confirm_modify_output => obj_fn_kw!(0, new_confirm_modify_output).as_obj(),

    /// def confirm_output_address(
    ///     *,
    ///     address: str,
    ///     address_label: str,
    ///     address_title: str,
    ///     chunkify: bool = False,
    /// ) -> object:
    ///     """Confirm output address."""
    Qstr::MP_QSTR_confirm_output_address => obj_fn_kw!(0, new_confirm_output_address).as_obj(),

    /// def confirm_output_amount(
    ///     *,
    ///     amount: str,
    ///     amount_title: str,
    /// ) -> object:
    ///     """Confirm output amount."""
    Qstr::MP_QSTR_confirm_output_amount => obj_fn_kw!(0, new_confirm_output_amount).as_obj(),

    /// def confirm_total(
    ///     *,
    ///     total_amount: str,
    ///     fee_amount: str,
    ///     fee_rate_amount: str | None,
    ///     account_label: str | None,
    ///     total_label: str,
    ///     fee_label: str,
    /// ) -> object:
    ///     """Confirm summary of a transaction."""
    Qstr::MP_QSTR_confirm_total => obj_fn_kw!(0, new_confirm_total).as_obj(),

    /// def altcoin_tx_summary(
    ///     *,
    ///     amount_title: str,
    ///     amount_value: str,
    ///     fee_title: str,
    ///     fee_value: str,
    ///     items: Iterable[Tuple[str, str]],
    ///     cancel_cross: bool = False,
    /// ) -> object:
    ///     """Confirm details about altcoin transaction."""
    Qstr::MP_QSTR_altcoin_tx_summary => obj_fn_kw!(0, new_altcoin_tx_summary).as_obj(),

    /// def tutorial() -> object:
    ///     """Show user how to interact with the device."""
    Qstr::MP_QSTR_tutorial => obj_fn_kw!(0, tutorial).as_obj(),

    /// def confirm_modify_fee(
    ///     *,
    ///     title: str,  # ignored
    ///     sign: int,
    ///     user_fee_change: str,
    ///     total_fee_new: str,
    ///     fee_rate_amount: str | None,
    /// ) -> object:
    ///     """Decrease or increase transaction fee."""
    Qstr::MP_QSTR_confirm_modify_fee => obj_fn_kw!(0, new_confirm_modify_fee).as_obj(),

    /// def confirm_fido(
    ///     *,
    ///     title: str,
    ///     app_name: str,
    ///     icon_name: str | None,  # unused on TR
    ///     accounts: list[str | None],
    /// ) -> int | object:
    ///     """FIDO confirmation.
    ///
    ///     Returns page index in case of confirmation and CANCELLED otherwise.
    ///     """
    Qstr::MP_QSTR_confirm_fido => obj_fn_kw!(0, new_confirm_fido).as_obj(),

    /// def multiple_pages_texts(
    ///     *,
    ///     title: str,
    ///     verb: str,
    ///     items: list[str],
    /// ) -> object:
    ///     """Show multiple texts, each on its own page."""
    Qstr::MP_QSTR_multiple_pages_texts => obj_fn_kw!(0, new_multiple_pages_texts).as_obj(),

    /// def show_warning(
    ///     *,
    ///     button: str,
    ///     warning: str,
    ///     description: str,
    /// ) -> object:
    ///     """Warning modal with middle button and centered text."""
    Qstr::MP_QSTR_show_warning => obj_fn_kw!(0, new_show_warning).as_obj(),

    /// def show_info(
    ///     *,
    ///     title: str,
    ///     description: str = "",
    ///     time_ms: int = 0,
    /// ) -> object:
    ///     """Info modal."""
    Qstr::MP_QSTR_show_info => obj_fn_kw!(0, new_show_info).as_obj(),

    /// def show_passphrase() -> object:
    ///     """Show passphrase on host dialog."""
    Qstr::MP_QSTR_show_passphrase => obj_fn_0!(new_show_passphrase).as_obj(),

    /// def show_mismatch(*, title: str) -> object:
    ///     """Warning modal, receiving address mismatch."""
    Qstr::MP_QSTR_show_mismatch => obj_fn_kw!(0, new_show_mismatch).as_obj(),

    /// def confirm_with_info(
    ///     *,
    ///     title: str,
    ///     button: str,
    ///     info_button: str,  # unused on TR
    ///     items: Iterable[Tuple[int, str]],
    ///     verb_cancel: str | None = None,
    /// ) -> object:
    ///     """Confirm given items but with third button. Always single page
    ///     without scrolling."""
    Qstr::MP_QSTR_confirm_with_info => obj_fn_kw!(0, new_confirm_with_info).as_obj(),

    /// def confirm_more(
    ///     *,
    ///     title: str,
    ///     button: str,
    ///     items: Iterable[tuple[int, str]],
    /// ) -> object:
    ///     """Confirm long content with the possibility to go back from any page.
    ///     Meant to be used with confirm_with_info."""
    Qstr::MP_QSTR_confirm_more => obj_fn_kw!(0, new_confirm_more).as_obj(),

    /// def confirm_coinjoin(
    ///     *,
    ///     max_rounds: str,
    ///     max_feerate: str,
    /// ) -> object:
    ///     """Confirm coinjoin authorization."""
    Qstr::MP_QSTR_confirm_coinjoin => obj_fn_kw!(0, new_confirm_coinjoin).as_obj(),

    /// def request_pin(
    ///     *,
    ///     prompt: str,
    ///     subprompt: str,
    ///     allow_cancel: bool = True,  # unused on TR
    ///     wrong_pin: bool = False,  # unused on TR
    /// ) -> str | object:
    ///     """Request pin on device."""
    Qstr::MP_QSTR_request_pin => obj_fn_kw!(0, new_request_pin).as_obj(),

    /// def request_passphrase(
    ///     *,
    ///     prompt: str,
    ///     max_len: int,  # unused on TR
    /// ) -> str | object:
    ///     """Get passphrase."""
    Qstr::MP_QSTR_request_passphrase => obj_fn_kw!(0, new_request_passphrase).as_obj(),

    /// def request_bip39(
    ///     *,
    ///     prompt: str,
    ///     prefill_word: str,
    ///     can_go_back: bool,
    /// ) -> str:
    ///     """Get recovery word for BIP39."""
    Qstr::MP_QSTR_request_bip39 => obj_fn_kw!(0, new_request_bip39).as_obj(),

    /// def request_slip39(
    ///     *,
    ///     prompt: str,
    ///     prefill_word: str,
    ///     can_go_back: bool,
    /// ) -> str:
    ///    """SLIP39 word input keyboard."""
    Qstr::MP_QSTR_request_slip39 => obj_fn_kw!(0, new_request_slip39).as_obj(),

    /// def select_word(
    ///     *,
    ///     title: str,  # unused on TR
    ///     description: str,
    ///     words: Iterable[str],
    /// ) -> int:
    ///    """Select mnemonic word from three possibilities - seed check after backup. The
    ///    iterable must be of exact size. Returns index in range `0..3`."""
    Qstr::MP_QSTR_select_word => obj_fn_kw!(0, new_select_word).as_obj(),

    /// def show_share_words(
    ///     *,
    ///     share_words: Iterable[str],
    /// ) -> object:
    ///     """Shows a backup seed."""
    Qstr::MP_QSTR_show_share_words => obj_fn_kw!(0, new_show_share_words).as_obj(),

    /// def request_number(
    ///     *,
    ///     title: str,
    ///     count: int,
    ///     min_count: int,
    ///     max_count: int,
    ///     description: Callable[[int], str] | None = None,  # unused on TR
    /// ) -> object:
    ///    """Number input with + and - buttons, description, and info button."""
    Qstr::MP_QSTR_request_number => obj_fn_kw!(0, new_request_number).as_obj(),

    /// def show_checklist(
    ///     *,
    ///     title: str,  # unused on TR
    ///     items: Iterable[str],
    ///     active: int,
    ///     button: str,
    /// ) -> object:
    ///    """Checklist of backup steps. Active index is highlighted, previous items have check
    ///    mark next to them."""
    Qstr::MP_QSTR_show_checklist => obj_fn_kw!(0, new_show_checklist).as_obj(),

    /// def confirm_recovery(
    ///     *,
    ///     title: str,  # unused on TR
    ///     description: str,
    ///     button: str,
    ///     dry_run: bool,
    ///     info_button: bool,  # unused on TR
    ///     show_info: bool,
    /// ) -> object:
    ///    """Device recovery homescreen."""
    Qstr::MP_QSTR_confirm_recovery => obj_fn_kw!(0, new_confirm_recovery).as_obj(),

    /// def select_word_count(
    ///     *,
    ///     dry_run: bool,  # unused on TR
    /// ) -> int | str:  # TR returns str
    ///    """Select mnemonic word count from (12, 18, 20, 24, 33)."""
    Qstr::MP_QSTR_select_word_count => obj_fn_kw!(0, new_select_word_count).as_obj(),

    /// def show_group_share_success(
    ///     *,
    ///     lines: Iterable[str],
    /// ) -> int:
    ///    """Shown after successfully finishing a group."""
    Qstr::MP_QSTR_show_group_share_success => obj_fn_kw!(0, new_show_group_share_success).as_obj(),

    /// def show_progress(
    ///     *,
    ///     title: str,
    ///     indeterminate: bool = False,
    ///     description: str = "",
    /// ) -> object:
    ///    """Show progress loader. Please note that the number of lines reserved on screen for
    ///    description is determined at construction time. If you want multiline descriptions
    ///    make sure the initial description has at least that amount of lines."""
    Qstr::MP_QSTR_show_progress => obj_fn_kw!(0, new_show_progress).as_obj(),

    /// def show_progress_coinjoin(
    ///     *,
    ///     title: str,
    ///     indeterminate: bool = False,
    ///     time_ms: int = 0,
    ///     skip_first_paint: bool = False,
    /// ) -> object:
    ///    """Show progress loader for coinjoin. Returns CANCELLED after a specified time when
    ///    time_ms timeout is passed."""
    Qstr::MP_QSTR_show_progress_coinjoin => obj_fn_kw!(0, new_show_progress_coinjoin).as_obj(),

    /// def show_homescreen(
    ///     *,
    ///     label: str | None,
    ///     hold: bool,  # unused on TR
    ///     notification: str | None,
    ///     notification_level: int = 0,
    ///     skip_first_paint: bool,
    /// ) -> CANCELLED:
    ///     """Idle homescreen."""
    Qstr::MP_QSTR_show_homescreen => obj_fn_kw!(0, new_show_homescreen).as_obj(),

    /// def show_lockscreen(
    ///     *,
    ///     label: str | None,
    ///     bootscreen: bool,
    ///     skip_first_paint: bool,
    ///     coinjoin_authorized: bool = False,
    /// ) -> CANCELLED:
    ///     """Homescreen for locked device."""
    Qstr::MP_QSTR_show_lockscreen => obj_fn_kw!(0, new_show_lockscreen).as_obj(),

    /// def confirm_firmware_update(
    ///     *,
    ///     description: str,
    ///     fingerprint: str,
    /// ) -> None:
    ///     """Ask whether to update firmware, optionally show fingerprint. Shared with bootloader."""
    Qstr::MP_QSTR_confirm_firmware_update => obj_fn_kw!(0, new_confirm_firmware_update).as_obj(),

    /// def show_wait_text(/, message: str) -> None:
    ///     """Show single-line text in the middle of the screen."""
    Qstr::MP_QSTR_show_wait_text => obj_fn_1!(new_show_wait_text).as_obj(),
};
