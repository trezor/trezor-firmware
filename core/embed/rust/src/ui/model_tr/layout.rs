use core::{cmp::Ordering, convert::TryInto};

use heapless::Vec;

use crate::{
    error::Error,
    micropython::{
        buffer::StrBuffer,
        gc::Gc,
        iter::{Iter, IterBuf},
        list::List,
        map::Map,
        module::Module,
        obj::Obj,
        qstr::Qstr,
        util,
    },
    ui::{
        component::{
            base::Component,
            paginated::{PageMsg, Paginate},
            text::{
                paragraphs::{
                    Checklist, Paragraph, ParagraphSource, ParagraphVecLong, ParagraphVecShort,
                    Paragraphs, VecExt,
                },
                TextStyle,
            },
            ComponentExt, Empty, LineBreaking, Timeout, TimeoutMsg,
        },
        display::{self, Font, Icon},
        geometry::Alignment,
        layout::{
            obj::{ComponentMsgObj, LayoutObj},
            result::{CANCELLED, CONFIRMED, INFO},
            util::{
                iter_into_array, iter_into_objs, iter_into_vec, upy_disable_animation, ConfirmBlob,
            },
        },
        model_tr::component::{ScrollableContent, ScrollableFrame},
    },
};

use super::{
    component::{
        ButtonActions, ButtonDetails, ButtonLayout, ButtonPage, CancelInfoConfirmMsg, Flow,
        FlowMsg, FlowPages, Frame, Homescreen, HomescreenMsg, Lockscreen, NoBtnDialog,
        NoBtnDialogMsg, NumberInput, NumberInputMsg, Page, PassphraseEntry, PassphraseEntryMsg,
        PinEntry, PinEntryMsg, Progress, ShareWords, ShowMore, SimpleChoice, SimpleChoiceMsg,
        WordlistEntry, WordlistEntryMsg, WordlistType,
    },
    constant, theme,
};

pub enum CancelConfirmMsg {
    Cancelled,
    Confirmed,
}

impl TryFrom<CancelConfirmMsg> for Obj {
    type Error = Error;

    fn try_from(value: CancelConfirmMsg) -> Result<Self, Self::Error> {
        match value {
            CancelConfirmMsg::Cancelled => Ok(CANCELLED.as_obj()),
            CancelConfirmMsg::Confirmed => Ok(CONFIRMED.as_obj()),
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

impl<T, U> ComponentMsgObj for NoBtnDialog<T, U>
where
    T: Component,
    U: Component,
    <U as Component>::Msg: TryInto<Obj, Error = Error>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            NoBtnDialogMsg::Controls(msg) => msg.try_into(),
        }
    }
}

impl<T> ComponentMsgObj for ButtonPage<T>
where
    T: Component + Paginate,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            PageMsg::Content(_) => Err(Error::TypeError),
            PageMsg::Controls(true) => Ok(CONFIRMED.as_obj()),
            PageMsg::Controls(false) => Ok(CANCELLED.as_obj()),
            PageMsg::Aux(_) => Err(Error::TypeError),
        }
    }
}

impl<F, const M: usize> ComponentMsgObj for Flow<F, M>
where
    F: Fn(usize) -> Page<M>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            FlowMsg::Confirmed => Ok(CONFIRMED.as_obj()),
            FlowMsg::Cancelled => Ok(CANCELLED.as_obj()),
            FlowMsg::ConfirmedIndex(index) => index.try_into(),
        }
    }
}

impl ComponentMsgObj for PinEntry {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            PinEntryMsg::Confirmed => self.pin().try_into(),
            PinEntryMsg::Cancelled => Ok(CANCELLED.as_obj()),
        }
    }
}

impl ComponentMsgObj for NumberInput {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            NumberInputMsg::Number(choice) => choice.try_into(),
        }
    }
}

impl<const N: usize> ComponentMsgObj for SimpleChoice<N> {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            SimpleChoiceMsg::Result(choice) => choice.as_str().try_into(),
            SimpleChoiceMsg::Index(index) => index.try_into(),
        }
    }
}

impl ComponentMsgObj for WordlistEntry {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            WordlistEntryMsg::ResultWord(word) => word.as_str().try_into(),
        }
    }
}

impl ComponentMsgObj for PassphraseEntry {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            PassphraseEntryMsg::Confirmed => self.passphrase().try_into(),
            PassphraseEntryMsg::Cancelled => Ok(CANCELLED.as_obj()),
        }
    }
}

impl<T> ComponentMsgObj for Frame<T>
where
    T: ComponentMsgObj,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        self.inner().msg_try_into_obj(msg)
    }
}

impl<T> ComponentMsgObj for ScrollableFrame<T>
where
    T: ComponentMsgObj + ScrollableContent,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        self.inner().msg_try_into_obj(msg)
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

/// Function to create and call a `ButtonPage` dialog based on `Paragraphs`
/// Has optional title (supply empty `StrBuffer` for that) and hold-to-confirm
/// functionality.
fn paragraphs_in_button_page<T: ParagraphSource + 'static>(
    title: StrBuffer,
    paragraphs: Paragraphs<T>,
    verb: StrBuffer,
    verb_cancel: Option<StrBuffer>,
    hold: bool,
) -> Result<Obj, Error> {
    // Left button - icon, text or nothing.
    let cancel_btn = if let Some(verb_cancel) = verb_cancel {
        if !verb_cancel.is_empty() {
            Some(ButtonDetails::text(verb_cancel))
        } else {
            Some(ButtonDetails::cancel_icon())
        }
    } else {
        None
    };

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

    let content = ButtonPage::new(paragraphs, theme::BG)
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
        let verb: StrBuffer = kwargs.get_or(Qstr::MP_QSTR_verb, "CONFIRM".into())?;
        let verb_cancel: Option<StrBuffer> = kwargs
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
                    .add(Paragraph::new(&theme::TEXT_MONO, description));
            } else {
                paragraphs
                    .add(Paragraph::new(&theme::TEXT_MONO, description))
                    .add(Paragraph::new(&theme::TEXT_BOLD, action));
            }
            paragraphs.into_paragraphs()
        };

        paragraphs_in_button_page(title, paragraphs, verb, verb_cancel, hold)
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
        let verb: StrBuffer = kwargs.get_or(Qstr::MP_QSTR_verb, "CONFIRM".into())?;
        let verb_cancel: Option<StrBuffer> = kwargs
            .get(Qstr::MP_QSTR_verb_cancel)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;

        let paragraphs = ConfirmBlob {
            description: description.unwrap_or_else(StrBuffer::empty),
            extra: extra.unwrap_or_else(StrBuffer::empty),
            data: data.try_into()?,
            description_font: &theme::TEXT_BOLD,
            extra_font: &theme::TEXT_MONO,
            data_font: &theme::TEXT_MONO_DATA,
        }
        .into_paragraphs();

        paragraphs_in_button_page(title, paragraphs, verb, verb_cancel, hold)
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_properties(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;

        let mut paragraphs = ParagraphVecLong::new();

        let mut iter_buf = IterBuf::new();
        let iter = Iter::try_from_obj_with_buf(items, &mut iter_buf)?;
        for para in iter {
            let [key, value, is_data]: [Obj; 3] = iter_into_objs(para)?;
            let key = key.try_into_option::<StrBuffer>()?;
            let value = value.try_into_option::<StrBuffer>()?;
            let is_data: bool = is_data.try_into()?;

            if let Some(key) = key {
                if value.is_some() {
                    paragraphs.add(Paragraph::new(&theme::TEXT_BOLD, key).no_break());
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

        paragraphs_in_button_page(
            title,
            paragraphs.into_paragraphs(),
            "CONFIRM".into(),
            None,
            hold,
        )
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_reset_device(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let button: StrBuffer = kwargs.get(Qstr::MP_QSTR_button)?.try_into()?;

        let description: StrBuffer =
            "By continuing you agree to Trezor Company's terms and conditions.".into();
        let url: StrBuffer = "More info at trezor.io/tos".into();

        let paragraphs = Paragraphs::new([
            Paragraph::new(&theme::TEXT_MONO, description),
            Paragraph::new(&theme::TEXT_BOLD, url),
        ]);

        paragraphs_in_button_page(title, paragraphs, button, None, false)
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_value(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: StrBuffer = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let value: StrBuffer = kwargs.get(Qstr::MP_QSTR_value)?.try_into()?;

        let verb: Option<StrBuffer> = kwargs
            .get(Qstr::MP_QSTR_verb)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;

        let paragraphs = Paragraphs::new([
            Paragraph::new(&theme::TEXT_BOLD, description),
            Paragraph::new(&theme::TEXT_MONO, value),
        ]);

        paragraphs_in_button_page(
            title,
            paragraphs,
            verb.unwrap_or_else(|| "CONFIRM".into()),
            None,
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
            Paragraph::new(&theme::TEXT_BOLD, "You are contributing:".into()),
            Paragraph::new(&theme::TEXT_MONO, spending_amount),
            Paragraph::new(&theme::TEXT_BOLD, "To the total amount:".into()),
            Paragraph::new(&theme::TEXT_MONO, total_amount),
        ]);

        paragraphs_in_button_page(
            "JOINT TRANSACTION".into(),
            paragraphs,
            "HOLD TO CONFIRM".into(),
            None,
            true,
        )
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_modify_output(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let address: StrBuffer = kwargs.get(Qstr::MP_QSTR_address)?.try_into()?;
        let sign: i32 = kwargs.get(Qstr::MP_QSTR_sign)?.try_into()?;
        let amount_change: StrBuffer = kwargs.get(Qstr::MP_QSTR_amount_change)?.try_into()?;
        let amount_new: StrBuffer = kwargs.get(Qstr::MP_QSTR_amount_new)?.try_into()?;

        let description = if sign < 0 {
            "Decrease amount by:"
        } else {
            "Increase amount by:"
        };

        let paragraphs = Paragraphs::new([
            Paragraph::new(&theme::TEXT_BOLD, "Address:".into()),
            Paragraph::new(&theme::TEXT_MONO, address).break_after(),
            Paragraph::new(&theme::TEXT_MONO, description.into()),
            Paragraph::new(&theme::TEXT_MONO, amount_change),
            Paragraph::new(&theme::TEXT_BOLD, "New amount:".into()),
            Paragraph::new(&theme::TEXT_MONO, amount_new),
        ]);

        paragraphs_in_button_page(
            "MODIFY AMOUNT".into(),
            paragraphs,
            "CONFIRM".into(),
            None,
            false,
        )
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_output(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let address: StrBuffer = kwargs.get(Qstr::MP_QSTR_address)?.try_into()?;
        let amount: StrBuffer = kwargs.get(Qstr::MP_QSTR_amount)?.try_into()?;
        let address_title: StrBuffer = kwargs.get(Qstr::MP_QSTR_address_title)?.try_into()?;
        let amount_title: StrBuffer = kwargs.get(Qstr::MP_QSTR_amount_title)?.try_into()?;

        let get_page = move |page_index| {
            // Showing two screens - the recipient address and summary confirmation
            match page_index {
                0 => {
                    // RECIPIENT + address
                    let btn_layout = ButtonLayout::cancel_none_text("CONFIRM".into());
                    let btn_actions = ButtonActions::cancel_none_next();
                    // Not putting hyphens in the address
                    Page::<10>::new(btn_layout, btn_actions, Font::MONO)
                        .with_line_breaking(LineBreaking::BreakWordsNoHyphen)
                        .with_title(address_title)
                        .text_mono(address)
                }
                1 => {
                    // AMOUNT + amount
                    let btn_layout = ButtonLayout::up_arrow_none_text("CONFIRM".into());
                    let btn_actions = ButtonActions::prev_none_confirm();
                    Page::<10>::new(btn_layout, btn_actions, Font::MONO)
                        .with_title(amount_title)
                        .newline()
                        .text_mono(amount)
                }
                _ => unreachable!(),
            }
        };
        let pages = FlowPages::new(get_page, 2);

        let obj = LayoutObj::new(Flow::new(pages).with_common_title(address_title))?;
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
        let total_label: StrBuffer = kwargs.get(Qstr::MP_QSTR_total_label)?.try_into()?;
        let fee_label: StrBuffer = kwargs.get(Qstr::MP_QSTR_fee_label)?.try_into()?;

        let get_page = move |page_index| {
            // Total amount + fee
            assert!(page_index == 0);

            let btn_layout = ButtonLayout::cancel_none_htc("HOLD TO CONFIRM".into());
            let btn_actions = ButtonActions::cancel_none_confirm();

            let mut flow_page = Page::<15>::new(btn_layout, btn_actions, Font::MONO)
                .text_bold(total_label)
                .newline()
                .text_mono(total_amount)
                .newline()
                .text_bold(fee_label)
                .newline()
                .text_mono(fee_amount);

            // Fee rate amount might not be there
            if let Some(fee_rate_amount) = fee_rate_amount {
                flow_page = flow_page.newline().text_mono(fee_rate_amount)
            }

            flow_page
        };
        let pages = FlowPages::new(get_page, 1);

        let obj = LayoutObj::new(Flow::new(pages))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_receive_address(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let address: StrBuffer = kwargs.get(Qstr::MP_QSTR_address)?.try_into()?;
        let address_qr: StrBuffer = kwargs.get(Qstr::MP_QSTR_address_qr)?.try_into()?;
        let account: StrBuffer = kwargs.get(Qstr::MP_QSTR_account)?.try_into()?;
        let derivation_path: StrBuffer = kwargs.get(Qstr::MP_QSTR_derivation_path)?.try_into()?;
        let case_sensitive: bool = kwargs.get(Qstr::MP_QSTR_case_sensitive)?.try_into()?;

        let get_page = move |page_index| {
            // Showing two screens - the recipient address and summary confirmation
            match page_index {
                0 => {
                    // RECEIVE ADDRESS
                    let btn_layout = ButtonLayout::cancel_armed_text("CONFIRM".into(), "i".into());
                    let btn_actions = ButtonActions::last_confirm_next();
                    Page::<15>::new(btn_layout, btn_actions, Font::BOLD)
                        .with_line_breaking(LineBreaking::BreakWordsNoHyphen)
                        .text_bold(title)
                        .newline()
                        .newline_half()
                        .text_mono(address)
                }
                1 => {
                    // QR CODE
                    let btn_layout = ButtonLayout::arrow_none_arrow();
                    let btn_actions = ButtonActions::prev_none_next();
                    Page::<15>::new(btn_layout, btn_actions, Font::MONO).qr_code(
                        address_qr,
                        theme::QR_SIDE_MAX,
                        case_sensitive,
                        constant::screen().center(),
                    )
                }
                2 => {
                    // ADDRESS INFO
                    let btn_layout = ButtonLayout::arrow_none_none();
                    let btn_actions = ButtonActions::prev_none_none();
                    Page::<15>::new(btn_layout, btn_actions, Font::MONO)
                        .with_line_breaking(LineBreaking::BreakWordsNoHyphen)
                        .text_bold("Account:".into())
                        .newline()
                        .text_mono(account)
                        .newline()
                        .text_bold("Derivation path:".into())
                        .newline()
                        .text_mono(derivation_path)
                }
                3 => {
                    // ADDRESS MISMATCH
                    let btn_layout = ButtonLayout::arrow_none_text("QUIT".into());
                    let btn_actions = ButtonActions::beginning_none_cancel();
                    Page::<15>::new(btn_layout, btn_actions, Font::MONO)
                        .text_bold("ADDRESS MISMATCH?".into())
                        .newline()
                        .newline_half()
                        .text_mono("Please contact Trezor support at trezor.io/support".into())
                }
                _ => unreachable!(),
            }
        };
        let pages = FlowPages::new(get_page, 4);

        let obj = LayoutObj::new(Flow::new(pages))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

/// General pattern of most tutorial screens.
/// (title, text, btn_layout, btn_actions)
fn tutorial_screen(
    title: StrBuffer,
    text: StrBuffer,
    btn_layout: ButtonLayout,
    btn_actions: ButtonActions,
) -> Page<10> {
    let mut page = Page::<10>::new(
        btn_layout,
        btn_actions,
        if !title.is_empty() {
            Font::BOLD
        } else {
            Font::MONO
        },
    );
    // Add title if present
    if !title.is_empty() {
        page = page.text_bold(title).newline().newline_half()
    }
    page = page.text_mono(text);
    page
}

extern "C" fn tutorial(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], _kwargs: &Map| {
        const PAGE_COUNT: usize = 7;

        let get_page = |page_index| {
            // Lazy-loaded list of screens to show, with custom content,
            // buttons and actions triggered by these buttons.
            // Cancelling the first screen will point to the last one,
            // which asks for confirmation whether user wants to
            // really cancel the tutorial.
            match page_index {
                // title, text, btn_layout, btn_actions
                0 => {
                    tutorial_screen(
                        "HELLO".into(),
                        "Welcome to Trezor.\nPress right to continue.".into(),
                        ButtonLayout::text_none_arrow("SKIP".into()),
                        ButtonActions::last_none_next(),
                    )
                },
                1 => {
                    tutorial_screen(
                        "".into(),
                        "Use Trezor by clicking left and right buttons.\n\nContinue right.".into(),
                        ButtonLayout::arrow_none_arrow(),
                        ButtonActions::prev_none_next(),
                    )
                },
                2 => {
                    tutorial_screen(
                        "HOLD TO CONFIRM".into(),
                        "Press and hold right to approve important operations.".into(),
                        ButtonLayout::arrow_none_htc("HOLD TO CONFIRM".into()),
                        ButtonActions::prev_none_next(),
                    )
                },
                3 => {
                    tutorial_screen(
                        "SCREEN SCROLL".into(),
                        "Press right to scroll down to read all content when text\ndoesn't fit on one screen. Press left to scroll up.".into(),
                        ButtonLayout::arrow_none_text("CONTINUE".into()),
                        ButtonActions::prev_none_next(),
                    )
                },
                4 => {
                    tutorial_screen(
                        "CONFIRM".into(),
                        "Press both left and right at the same time to confirm.".into(),
                        ButtonLayout::none_armed_none("CONFIRM".into()),
                        ButtonActions::prev_next_none(),
                    )
                },
                // This page is special
                5 => {
                    Page::<10>::new(
                        ButtonLayout::text_none_text("AGAIN".into(), "FINISH".into()),
                        ButtonActions::beginning_none_confirm(),
                        Font::MONO,
                    )
                        .newline()
                        .text_mono("Tutorial complete.".into())
                        .newline()
                        .newline()
                        .alignment(Alignment::Center)
                        .text_bold("You're ready to\nuse Trezor.".into())
                },
                6 => {
                    tutorial_screen(
                        "SKIP TUTORIAL".into(),
                        "Are you sure you want to skip the tutorial?".into(),
                        ButtonLayout::cancel_none_text("SKIP".into()),
                        ButtonActions::beginning_none_cancel(),
                    )
                },
                _ => unreachable!(),
            }
        };

        let pages = FlowPages::new(get_page, PAGE_COUNT);

        let obj = LayoutObj::new(Flow::new(pages))?;
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
            s if s < 0 => ("Decrease fee by:", user_fee_change),
            s if s > 0 => ("Increase fee by:", user_fee_change),
            _ => ("Your fee did not change.", StrBuffer::empty()),
        };

        let mut paragraphs_vec = ParagraphVecShort::new();
        paragraphs_vec
            .add(Paragraph::new(&theme::TEXT_BOLD, description.into()))
            .add(Paragraph::new(&theme::TEXT_MONO, change))
            .add(Paragraph::new(&theme::TEXT_BOLD, "Transaction fee:".into()).no_break())
            .add(Paragraph::new(&theme::TEXT_MONO, total_fee_new));

        if let Some(fee_rate_amount) = fee_rate_amount {
            paragraphs_vec
                .add(Paragraph::new(&theme::TEXT_BOLD, "Fee rate:".into()).no_break())
                .add(Paragraph::new(&theme::TEXT_MONO, fee_rate_amount));
        }

        paragraphs_in_button_page(
            "MODIFY FEE".into(),
            paragraphs_vec.into_paragraphs(),
            "CONFIRM".into(),
            Some("".into()),
            false,
        )
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_fido(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let app_name: StrBuffer = kwargs.get(Qstr::MP_QSTR_app_name)?.try_into()?;
        let accounts: Gc<List> = kwargs.get(Qstr::MP_QSTR_accounts)?.try_into()?;

        // Cache the page count so that we can move `accounts` into the closure.
        let page_count = accounts.len();

        let title: StrBuffer = if page_count > 1 {
            "IMPORT".into()
        } else {
            "IMPORT CREDENTIAL".into()
        };

        // Closure to lazy-load the information on given page index.
        // Done like this to allow arbitrarily many pages without
        // the need of any allocation here in Rust.
        let get_page = move |page_index| {
            let account_obj = unwrap!(accounts.get(page_index as usize));
            let account = account_obj.try_into().unwrap_or_else(|_| "".into());

            let (btn_layout, btn_actions) = if page_count == 1 {
                // There is only one page
                (
                    ButtonLayout::cancel_none_text("CONFIRM".into()),
                    ButtonActions::cancel_none_confirm(),
                )
            } else if page_index == 0 {
                // First page
                (
                    ButtonLayout::cancel_armed_arrow("SELECT".into()),
                    ButtonActions::cancel_confirm_next(),
                )
            } else if page_index as usize == page_count - 1 {
                // Last page
                (
                    ButtonLayout::arrow_armed_none("SELECT".into()),
                    ButtonActions::prev_confirm_none(),
                )
            } else {
                // Page in the middle
                (
                    ButtonLayout::arrow_armed_arrow("SELECT".into()),
                    ButtonActions::prev_confirm_next(),
                )
            };

            Page::<10>::new(btn_layout, btn_actions, Font::MONO)
                .newline()
                .text_mono(app_name)
                .newline()
                .text_bold(account)
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

extern "C" fn new_show_info(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: StrBuffer =
            kwargs.get_or(Qstr::MP_QSTR_description, StrBuffer::empty())?;
        let time_ms: u32 = kwargs.get_or(Qstr::MP_QSTR_time_ms, 0)?;

        let content = Frame::new(
            title,
            Paragraphs::new([Paragraph::new(&theme::TEXT_MONO, description)]),
        );
        let obj = if time_ms == 0 {
            // No timer, used when we only want to draw the dialog once and
            // then throw away the layout object.
            LayoutObj::new(NoBtnDialog::new(content, Empty))?
        } else {
            // Timeout.
            LayoutObj::new(NoBtnDialog::new(
                content,
                Timeout::new(time_ms).map(|msg| {
                    (matches!(msg, TimeoutMsg::TimedOut)).then(|| CancelConfirmMsg::Confirmed)
                }),
            ))?
        };

        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_with_info(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;

        let mut paragraphs = ParagraphVecShort::new();

        let mut iter_buf = IterBuf::new();
        let iter = Iter::try_from_obj_with_buf(items, &mut iter_buf)?;
        for para in iter {
            let [font, text]: [Obj; 2] = iter_into_objs(para)?;
            let style: &TextStyle = theme::textstyle_number_bold_or_mono(font.try_into()?);
            let text: StrBuffer = text.try_into()?;
            paragraphs.add(Paragraph::new(style, text));
            if paragraphs.is_full() {
                break;
            }
        }

        let obj = LayoutObj::new(Frame::new(
            title,
            ShowMore::new(paragraphs.into_paragraphs()),
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_coinjoin(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let max_rounds: StrBuffer = kwargs.get(Qstr::MP_QSTR_max_rounds)?.try_into()?;
        let max_feerate: StrBuffer = kwargs.get(Qstr::MP_QSTR_max_feerate)?.try_into()?;

        let paragraphs = Paragraphs::new([
            Paragraph::new(&theme::TEXT_BOLD, "Maximum rounds:".into()),
            Paragraph::new(&theme::TEXT_MONO, max_rounds),
            Paragraph::new(&theme::TEXT_BOLD, "Maximum mining fee:".into()).no_break(),
            Paragraph::new(&theme::TEXT_MONO, max_feerate),
        ]);

        paragraphs_in_button_page(
            "AUTHORIZE COINJOIN".into(),
            paragraphs,
            "HOLD TO CONFIRM".into(),
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
        let _max_len: u8 = kwargs.get(Qstr::MP_QSTR_max_len)?.try_into()?;

        let obj = LayoutObj::new(Frame::new(prompt, PassphraseEntry::new()).with_title_centered())?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_bip39(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let prompt: StrBuffer = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;

        let obj = LayoutObj::new(
            Frame::new(prompt, WordlistEntry::new(WordlistType::Bip39)).with_title_centered(),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_slip39(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let prompt: StrBuffer = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;

        let obj = LayoutObj::new(
            Frame::new(prompt, WordlistEntry::new(WordlistType::Slip39)).with_title_centered(),
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
        let words: Vec<StrBuffer, 3> = iter_into_vec(words_iterable)?;

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
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let share_words_obj: Obj = kwargs.get(Qstr::MP_QSTR_share_words)?;
        let share_words: Vec<StrBuffer, 33> = iter_into_vec(share_words_obj)?;

        let confirm_btn =
            Some(ButtonDetails::text("HOLD TO CONFIRM".into()).with_default_duration());

        let obj = LayoutObj::new(
            ButtonPage::new(ShareWords::new(title, share_words), theme::BG)
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
        let _title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let button: StrBuffer = kwargs.get(Qstr::MP_QSTR_button)?.try_into()?;
        let active: usize = kwargs.get(Qstr::MP_QSTR_active)?.try_into()?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;

        let mut iter_buf = IterBuf::new();
        let mut paragraphs = ParagraphVecLong::new();
        let iter = Iter::try_from_obj_with_buf(items, &mut iter_buf)?;
        for (i, item) in iter.enumerate() {
            let style = match i.cmp(&active) {
                Ordering::Less => &theme::TEXT_MONO,
                Ordering::Equal => &theme::TEXT_BOLD,
                Ordering::Greater => &theme::TEXT_MONO,
            };
            let text: StrBuffer = item.try_into()?;
            paragraphs.add(Paragraph::new(style, text));
        }

        let confirm_btn = Some(ButtonDetails::text(button));

        let obj = LayoutObj::new(
            ButtonPage::new(
                Checklist::from_paragraphs(
                    Icon::new(theme::ICON_ARROW_RIGHT_FAT),
                    Icon::new(theme::ICON_TICK_FAT),
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
        let button: StrBuffer = kwargs.get(Qstr::MP_QSTR_button)?.try_into()?;
        let dry_run: bool = kwargs.get(Qstr::MP_QSTR_dry_run)?.try_into()?;

        let paragraphs = Paragraphs::new([Paragraph::new(&theme::TEXT_MONO, description)]);

        let title = if dry_run {
            "SEED CHECK"
        } else {
            "WALLET RECOVERY"
        };

        paragraphs_in_button_page(title.into(), paragraphs, button, Some("".into()), false)
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_select_word_count(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let _dry_run: bool = kwargs.get(Qstr::MP_QSTR_dry_run)?.try_into()?;
        let title = "NUMBER OF WORDS".into();

        let choices: Vec<StrBuffer, 5> = ["12", "18", "20", "24", "33"]
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
        let lines: [StrBuffer; 4] = iter_into_array(lines_iterable)?;

        let [l0, l1, l2, l3] = lines;

        let paragraphs = Paragraphs::new([
            Paragraph::new(&theme::TEXT_MONO, l0),
            Paragraph::new(&theme::TEXT_BOLD, l1),
            Paragraph::new(&theme::TEXT_MONO, l2),
            Paragraph::new(&theme::TEXT_BOLD, l3),
        ]);

        paragraphs_in_button_page("".into(), paragraphs, "CONTINUE".into(), None, false)
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
        let obj = LayoutObj::new(Progress::new(
            title,
            indeterminate,
            description,
            StrBuffer::alloc,
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_homescreen(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let label: StrBuffer = kwargs.get(Qstr::MP_QSTR_label)?.try_into()?;
        let notification: Option<StrBuffer> =
            kwargs.get(Qstr::MP_QSTR_notification)?.try_into_option()?;
        let notification_level: u8 = kwargs.get_or(Qstr::MP_QSTR_notification_level, 0)?;
        let _hold: bool = kwargs.get(Qstr::MP_QSTR_hold)?.try_into()?;
        let skip_first_paint: bool = kwargs.get(Qstr::MP_QSTR_skip_first_paint)?.try_into()?;

        let notification = notification.map(|w| (w, notification_level));
        let obj = LayoutObj::new(Homescreen::new(label, notification))?;
        if skip_first_paint {
            obj.skip_first_paint();
        }
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_lockscreen(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let label: StrBuffer = kwargs.get(Qstr::MP_QSTR_label)?.try_into()?;
        let bootscreen: bool = kwargs.get(Qstr::MP_QSTR_bootscreen)?.try_into()?;
        let skip_first_paint: bool = kwargs.get(Qstr::MP_QSTR_skip_first_paint)?.try_into()?;

        let obj = LayoutObj::new(Lockscreen::new(label, bootscreen))?;
        if skip_first_paint {
            obj.skip_first_paint();
        }
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_busyscreen(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: StrBuffer = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let time_ms: u32 = kwargs.get(Qstr::MP_QSTR_time_ms)?.try_into()?;
        let skip_first_paint: bool = kwargs.get(Qstr::MP_QSTR_skip_first_paint)?.try_into()?;

        let content = Paragraphs::new([
            Paragraph::new(&theme::TEXT_BOLD, title),
            Paragraph::new(&theme::TEXT_MONO, description),
        ]);

        let obj = LayoutObj::new(NoBtnDialog::new(
            content,
            Timeout::new(time_ms).map(|msg| {
                (matches!(msg, TimeoutMsg::TimedOut)).then(|| CancelConfirmMsg::Confirmed)
            }),
        ))?;

        if skip_first_paint {
            obj.skip_first_paint();
        }
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn draw_welcome_screen() -> Obj {
    // TODO: create some welcome screen
    // No need of util::try_or_raise, this does not allocate
    // let mut screen = WelcomeScreen::new();
    // screen.place(constant::screen());
    display::sync();
    // screen.paint();
    display::set_backlight(150); // BACKLIGHT_NORMAL
    Obj::const_none()
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

    /// def confirm_blob(
    ///     *,
    ///     title: str,
    ///     data: str | bytes,
    ///     description: str | None,
    ///     extra: str | None,
    ///     verb_cancel: str | None = None,
    ///     hold: bool = False,
    /// ) -> object:
    ///     """Confirm byte sequence data."""
    Qstr::MP_QSTR_confirm_blob => obj_fn_kw!(0, new_confirm_blob).as_obj(),

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
    ///     address: str,
    ///     sign: int,
    ///     amount_change: str,
    ///     amount_new: str,
    /// ) -> object:
    ///     """Decrease or increase amount for given address."""
    Qstr::MP_QSTR_confirm_modify_output => obj_fn_kw!(0, new_confirm_modify_output).as_obj(),

    /// def confirm_output(
    ///     *,
    ///     address: str,
    ///     amount: str,
    ///     address_title: str,
    ///     amount_title: str,
    /// ) -> object:
    ///     """Confirm output."""
    Qstr::MP_QSTR_confirm_output => obj_fn_kw!(0, new_confirm_output).as_obj(),

    /// def confirm_total(
    ///     *,
    ///     total_amount: str,
    ///     fee_amount: str,
    ///     fee_rate_amount: str | None = None,
    ///     total_label: str,
    ///     fee_label: str,
    /// ) -> object:
    ///     """Confirm summary of a transaction."""
    Qstr::MP_QSTR_confirm_total => obj_fn_kw!(0, new_confirm_total).as_obj(),

    /// def show_receive_address(
    ///     *,
    ///     title: str,
    ///     address: str,
    ///     address_qr: str,
    ///     account: str,
    ///     derivation_path: str,
    ///     case_sensitive: bool,
    /// ) -> object:
    ///     """Show receive address together with QR code and details about it."""
    Qstr::MP_QSTR_show_receive_address => obj_fn_kw!(0, new_show_receive_address).as_obj(),

    /// def tutorial() -> object:
    ///     """Show user how to interact with the device."""
    Qstr::MP_QSTR_tutorial => obj_fn_kw!(0, tutorial).as_obj(),

    /// def confirm_modify_fee(
    ///     *,
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

    /// def show_info(
    ///     *,
    ///     title: str,
    ///     description: str = "",
    ///     time_ms: int = 0,
    /// ) -> object:
    ///     """Info modal."""
    Qstr::MP_QSTR_show_info => obj_fn_kw!(0, new_show_info).as_obj(),

    /// def confirm_with_info(
    ///     *,
    ///     title: str,
    ///     button: str,  # unused on TR
    ///     info_button: str,  # unused on TR
    ///     items: Iterable[Tuple[int, str]],
    /// ) -> object:
    ///     """Confirm given items but with third button. Always single page
    ///     without scrolling."""
    Qstr::MP_QSTR_confirm_with_info => obj_fn_kw!(0, new_confirm_with_info).as_obj(),

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
    ///     max_len: int,
    /// ) -> str | object:
    ///     """Get passphrase."""
    Qstr::MP_QSTR_request_passphrase => obj_fn_kw!(0, new_request_passphrase).as_obj(),

    /// def request_bip39(
    ///     *,
    ///     prompt: str,
    /// ) -> str:
    ///     """Get recovery word for BIP39."""
    Qstr::MP_QSTR_request_bip39 => obj_fn_kw!(0, new_request_bip39).as_obj(),

    /// def request_slip39(
    ///     *,
    ///     prompt: str,
    /// ) -> str:
    ///    """SLIP39 word input keyboard."""
    Qstr::MP_QSTR_request_slip39 => obj_fn_kw!(0, new_request_slip39).as_obj(),

    /// def select_word(
    ///     *,
    ///     title: str,
    ///     description: str,
    ///     words: Iterable[str],
    /// ) -> int:
    ///    """Select mnemonic word from three possibilities - seed check after backup. The
    ///    iterable must be of exact size. Returns index in range `0..3`."""
    Qstr::MP_QSTR_select_word => obj_fn_kw!(0, new_select_word).as_obj(),

    /// def show_share_words(
    ///     *,
    ///     title: str,
    ///     share_words: Iterable[str],
    /// ) -> None:
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
    ///     title: str,
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
    /// ) -> object:
    ///    """Device recovery homescreen."""
    Qstr::MP_QSTR_confirm_recovery => obj_fn_kw!(0, new_confirm_recovery).as_obj(),

    /// def select_word_count(
    ///     *,
    ///     dry_run: bool,
    /// ) -> int | str:  # TR returns str
    ///    """Select mnemonic word count from (12, 18, 20, 24, 33)."""
    Qstr::MP_QSTR_select_word_count => obj_fn_kw!(0, new_select_word_count).as_obj(),

    /// def show_group_share_success(
    ///     *,
    ///     lines: Iterable[str]
    /// ) -> int:
    ///    """Shown after successfully finishing a group."""
    Qstr::MP_QSTR_show_group_share_success => obj_fn_kw!(0, new_show_group_share_success).as_obj(),

    /// def show_progress(
    ///     *,
    ///     title: str,
    ///     indeterminate: bool = False,
    ///     description: str | None = None,
    /// ) -> object:
    ///    """Show progress loader. Please note that the number of lines reserved on screen for
    ///    description is determined at construction time. If you want multiline descriptions
    ///    make sure the initial description has at least that amount of lines."""
    Qstr::MP_QSTR_show_progress => obj_fn_kw!(0, new_show_progress).as_obj(),

    /// def show_homescreen(
    ///     *,
    ///     label: str,
    ///     hold: bool,
    ///     notification: str | None,
    ///     notification_level: int = 0,
    ///     skip_first_paint: bool,
    /// ) -> CANCELLED:
    ///     """Idle homescreen."""
    Qstr::MP_QSTR_show_homescreen => obj_fn_kw!(0, new_show_homescreen).as_obj(),

    /// def show_lockscreen(
    ///     *,
    ///     label: str,
    ///     bootscreen: bool,
    ///     skip_first_paint: bool,
    /// ) -> CANCELLED:
    ///     """Homescreen for locked device."""
    Qstr::MP_QSTR_show_lockscreen => obj_fn_kw!(0, new_show_lockscreen).as_obj(),

    /// def show_busyscreen(
    ///     *,
    ///     title: str,
    ///     description: str,
    ///     time_ms: int,
    ///     skip_first_paint: bool,
    /// ) -> CANCELLED:
    ///     """Homescreen used for indicating coinjoin in progress."""
    Qstr::MP_QSTR_show_busyscreen => obj_fn_kw!(0, new_show_busyscreen).as_obj(),

    /// def draw_welcome_screen() -> None:
    ///     """Show logo icon with the model name at the bottom and return."""
    Qstr::MP_QSTR_draw_welcome_screen => obj_fn_0!(draw_welcome_screen).as_obj(),
};
