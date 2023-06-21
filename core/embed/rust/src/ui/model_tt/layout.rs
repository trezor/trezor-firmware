use core::{cmp::Ordering, convert::TryInto};
use cstr_core::cstr;

use crate::{
    error::Error,
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
    strutil::StringType,
    ui::{
        component::{
            base::ComponentExt,
            image::BlendedImage,
            paginated::{AuxPageMsg, PageMsg, Paginate},
            painter,
            placed::GridPlaced,
            text::{
                op::OpTextLayout,
                paragraphs::{
                    Checklist, Paragraph, ParagraphSource, ParagraphVecLong, ParagraphVecShort,
                    Paragraphs, VecExt,
                },
                TextStyle,
            },
            Border, Component, Empty, FormattedText, Never, Qr, Timeout,
        },
        display::{self, tjpgd::jpeg_info},
        geometry,
        layout::{
            obj::{ComponentMsgObj, LayoutObj},
            result::{CANCELLED, CONFIRMED, INFO},
            util::{
                iter_into_array, upy_disable_animation, upy_jpeg_info, upy_jpeg_test, ConfirmBlob,
                PropsList,
            },
        },
    },
};

use super::{
    component::{
        AddressDetails, Bip39Input, Button, ButtonMsg, ButtonStyleSheet, CancelConfirmMsg,
        CancelInfoConfirmMsg, CoinJoinProgress, Dialog, DialogMsg, FidoConfirm, FidoMsg, Frame,
        FrameMsg, HoldToConfirm, HoldToConfirmMsg, Homescreen, HomescreenMsg, HorizontalPage,
        IconDialog, Lockscreen, MnemonicInput, MnemonicKeyboard, MnemonicKeyboardMsg,
        NotificationFrame, NumberInputDialog, NumberInputDialogMsg, PassphraseKeyboard,
        PassphraseKeyboardMsg, PinKeyboard, PinKeyboardMsg, Progress, SelectWordCount,
        SelectWordCountMsg, SelectWordMsg, Slip39Input, SwipeHoldPage, SwipePage, WelcomeScreen,
    },
    constant, theme,
};

impl TryFrom<CancelConfirmMsg> for Obj {
    type Error = Error;

    fn try_from(value: CancelConfirmMsg) -> Result<Self, Self::Error> {
        match value {
            CancelConfirmMsg::Cancelled => Ok(CANCELLED.as_obj()),
            CancelConfirmMsg::Confirmed => Ok(CONFIRMED.as_obj()),
        }
    }
}

impl TryFrom<CancelInfoConfirmMsg> for Obj {
    type Error = Error;

    fn try_from(value: CancelInfoConfirmMsg) -> Result<Self, Self::Error> {
        match value {
            CancelInfoConfirmMsg::Cancelled => Ok(CANCELLED.as_obj()),
            CancelInfoConfirmMsg::Info => Ok(INFO.as_obj()),
            CancelInfoConfirmMsg::Confirmed => Ok(CONFIRMED.as_obj()),
        }
    }
}

impl TryFrom<SelectWordMsg> for Obj {
    type Error = Error;

    fn try_from(value: SelectWordMsg) -> Result<Self, Self::Error> {
        match value {
            SelectWordMsg::Selected(i) => i.try_into(),
        }
    }
}

impl TryFrom<SelectWordCountMsg> for Obj {
    type Error = Error;

    fn try_from(value: SelectWordCountMsg) -> Result<Self, Self::Error> {
        match value {
            SelectWordCountMsg::Selected(i) => i.try_into(),
        }
    }
}

impl<F, T, U> ComponentMsgObj for FidoConfirm<F, T, U>
where
    F: Fn(usize) -> T,
    T: StringType,
    U: Component<Msg = CancelConfirmMsg>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            FidoMsg::Confirmed(page) => Ok((page as u8).into()),
            FidoMsg::Cancelled => Ok(CANCELLED.as_obj()),
        }
    }
}

impl<T, U> ComponentMsgObj for Dialog<T, U>
where
    T: ComponentMsgObj,
    U: Component,
    <U as Component>::Msg: TryInto<Obj, Error = Error>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            DialogMsg::Content(c) => Ok(self.inner().msg_try_into_obj(c)?),
            DialogMsg::Controls(msg) => msg.try_into(),
        }
    }
}

impl<T, U> ComponentMsgObj for IconDialog<T, U>
where
    T: StringType,
    U: Component,
    <U as Component>::Msg: TryInto<Obj, Error = Error>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            DialogMsg::Controls(msg) => msg.try_into(),
            _ => unreachable!(),
        }
    }
}

impl<T> ComponentMsgObj for HoldToConfirm<T>
where
    T: ComponentMsgObj,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            HoldToConfirmMsg::Content(c) => Ok(self.inner().msg_try_into_obj(c)?),
            HoldToConfirmMsg::Confirmed => Ok(CONFIRMED.as_obj()),
            HoldToConfirmMsg::Cancelled => Ok(CANCELLED.as_obj()),
        }
    }
}

impl<T> ComponentMsgObj for PinKeyboard<T>
where
    T: AsRef<str>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            PinKeyboardMsg::Confirmed => self.pin().try_into(),
            PinKeyboardMsg::Cancelled => Ok(CANCELLED.as_obj()),
        }
    }
}

impl ComponentMsgObj for PassphraseKeyboard {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            PassphraseKeyboardMsg::Confirmed => self.passphrase().try_into(),
            PassphraseKeyboardMsg::Cancelled => Ok(CANCELLED.as_obj()),
        }
    }
}

impl<T, U> ComponentMsgObj for MnemonicKeyboard<T, U>
where
    T: MnemonicInput,
    U: AsRef<str>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            MnemonicKeyboardMsg::Confirmed => {
                if let Some(word) = self.mnemonic() {
                    word.try_into()
                } else {
                    panic!("invalid mnemonic")
                }
            }
        }
    }
}

impl<T, U> ComponentMsgObj for Frame<T, U>
where
    T: ComponentMsgObj,
    U: AsRef<str>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            FrameMsg::Content(c) => self.inner().msg_try_into_obj(c),
            FrameMsg::Button(b) => b.try_into(),
        }
    }
}

impl<T, U> ComponentMsgObj for NotificationFrame<T, U>
where
    T: ComponentMsgObj,
    U: AsRef<str>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        self.inner().msg_try_into_obj(msg)
    }
}

impl<T, U> ComponentMsgObj for SwipePage<T, U>
where
    T: Component + Paginate,
    U: Component,
    <U as Component>::Msg: TryInto<Obj, Error = Error>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            PageMsg::Content(_) => Err(Error::TypeError),
            PageMsg::Controls(msg) => msg.try_into(),
            PageMsg::Aux(AuxPageMsg::GoBack) => Ok(CANCELLED.as_obj()),
            PageMsg::Aux(AuxPageMsg::SwipeLeft) => Ok(INFO.as_obj()),
            PageMsg::Aux(AuxPageMsg::SwipeRight) => Ok(CANCELLED.as_obj()),
        }
    }
}

impl<T> ComponentMsgObj for SwipeHoldPage<T>
where
    T: Component + Paginate,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            PageMsg::Content(_) => Err(Error::TypeError),
            PageMsg::Controls(msg) => msg.try_into(),
            PageMsg::Aux(AuxPageMsg::GoBack) => Ok(CANCELLED.as_obj()),
            PageMsg::Aux(AuxPageMsg::SwipeLeft) => Ok(INFO.as_obj()),
            PageMsg::Aux(AuxPageMsg::SwipeRight) => Ok(CANCELLED.as_obj()),
        }
    }
}

impl<F> ComponentMsgObj for painter::Painter<F>
where
    F: FnMut(geometry::Rect),
{
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!()
    }
}

// Clippy/compiler complains about conflicting implementations
// TODO move the common impls to a common module
#[cfg(not(feature = "clippy"))]
impl<T> ComponentMsgObj for Paragraphs<T>
where
    T: ParagraphSource,
{
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!()
    }
}

impl<T> ComponentMsgObj for FormattedText<T>
where
    T: StringType + Clone,
{
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!()
    }
}

impl<T> ComponentMsgObj for Checklist<T>
where
    T: ParagraphSource,
{
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!()
    }
}

impl<T, F> ComponentMsgObj for NumberInputDialog<T, F>
where
    T: StringType,
    F: Fn(u32) -> T,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        let value = self.value().try_into()?;
        match msg {
            NumberInputDialogMsg::Selected => Ok((CONFIRMED.as_obj(), value).try_into()?),
            NumberInputDialogMsg::InfoRequested => Ok((CANCELLED.as_obj(), value).try_into()?),
        }
    }
}

impl<T> ComponentMsgObj for Border<T>
where
    T: ComponentMsgObj,
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
    T: AsRef<str>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            HomescreenMsg::Dismissed => Ok(CANCELLED.as_obj()),
        }
    }
}

impl<T> ComponentMsgObj for Lockscreen<T>
where
    T: AsRef<str>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            HomescreenMsg::Dismissed => Ok(CANCELLED.as_obj()),
        }
    }
}

impl<T, S> ComponentMsgObj for (GridPlaced<Paragraphs<T>>, GridPlaced<FormattedText<S>>)
where
    T: ParagraphSource,
    S: StringType + Clone,
{
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!()
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

impl ComponentMsgObj for Qr {
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!();
    }
}

impl<T> ComponentMsgObj for HorizontalPage<T>
where
    T: ComponentMsgObj + Paginate,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            PageMsg::Content(inner_msg) => Ok(self.inner().msg_try_into_obj(inner_msg)?),
            PageMsg::Controls(_) => Err(Error::TypeError),
            PageMsg::Aux(AuxPageMsg::GoBack) => Ok(CANCELLED.as_obj()),
            PageMsg::Aux(_) => Err(Error::TypeError),
        }
    }
}

impl<T> ComponentMsgObj for AddressDetails<T>
where
    T: StringType + Clone,
{
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        Ok(CANCELLED.as_obj())
    }
}

impl<T, U> ComponentMsgObj for CoinJoinProgress<T, U>
where
    T: AsRef<str>,
    U: Component<Msg = Never>,
{
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!();
    }
}

extern "C" fn new_confirm_action(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let action: Option<StrBuffer> = kwargs.get(Qstr::MP_QSTR_action)?.try_into_option()?;
        let description: Option<StrBuffer> =
            kwargs.get(Qstr::MP_QSTR_description)?.try_into_option()?;
        let verb: Option<StrBuffer> = kwargs
            .get(Qstr::MP_QSTR_verb)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let verb_cancel: Option<StrBuffer> = kwargs
            .get(Qstr::MP_QSTR_verb_cancel)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let reverse: bool = kwargs.get_or(Qstr::MP_QSTR_reverse, false)?;
        let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;
        let hold_danger: bool = kwargs.get_or(Qstr::MP_QSTR_hold_danger, false)?;

        let paragraphs = {
            let action = action.unwrap_or_default();
            let description = description.unwrap_or_default();
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

        let obj = if hold {
            let page = if hold_danger {
                SwipeHoldPage::with_danger(paragraphs, theme::BG)
            } else {
                SwipeHoldPage::new(paragraphs, theme::BG)
            };
            LayoutObj::new(Frame::left_aligned(theme::label_title(), title, page))?
        } else {
            let buttons = Button::cancel_confirm_text(verb_cancel, verb);
            LayoutObj::new(Frame::left_aligned(
                theme::label_title(),
                title,
                SwipePage::new(paragraphs, buttons, theme::BG).with_cancel_on_first_page(),
            ))?
        };
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_emphasized(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let verb: Option<StrBuffer> = kwargs
            .get(Qstr::MP_QSTR_verb)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;

        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;
        let mut ops = OpTextLayout::new(theme::TEXT_NORMAL);
        for item in IterBuf::new().try_iterate(items)? {
            if item.is_str() {
                ops = ops.text_normal(item.try_into()?)
            } else {
                let [emphasis, text]: [Obj; 2] = iter_into_array(item)?;
                let text: StrBuffer = text.try_into()?;
                if emphasis.try_into()? {
                    ops = ops.text_demibold(text);
                } else {
                    ops = ops.text_normal(text);
                }
            }
        }

        let buttons = Button::<StrBuffer>::cancel_confirm_text(None, verb);
        let obj = LayoutObj::new(Frame::left_aligned(
            theme::label_title(),
            title,
            SwipePage::new(
                FormattedText::new(ops).vertically_aligned(geometry::Alignment::Center),
                buttons,
                theme::BG,
            ),
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

struct ConfirmBlobParams {
    title: StrBuffer,
    subtitle: Option<StrBuffer>,
    data: Obj,
    description: Option<StrBuffer>,
    extra: Option<StrBuffer>,
    verb: Option<StrBuffer>,
    verb_cancel: Option<StrBuffer>,
    info_button: bool,
    hold: bool,
}

impl ConfirmBlobParams {
    fn new(
        title: StrBuffer,
        data: Obj,
        description: Option<StrBuffer>,
        verb: Option<StrBuffer>,
        verb_cancel: Option<StrBuffer>,
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
        }
    }

    fn with_extra(mut self, extra: Option<StrBuffer>) -> Self {
        self.extra = extra;
        self
    }

    fn with_subtitle(mut self, subtitle: Option<StrBuffer>) -> Self {
        self.subtitle = subtitle;
        self
    }

    fn with_info_button(mut self, info_button: bool) -> Self {
        self.info_button = info_button;
        self
    }

    fn into_layout(self) -> Result<Obj, Error> {
        let paragraphs = ConfirmBlob {
            description: self.description.unwrap_or_else(StrBuffer::empty),
            extra: self.extra.unwrap_or_else(StrBuffer::empty),
            data: self.data.try_into()?,
            description_font: &theme::TEXT_NORMAL,
            extra_font: &theme::TEXT_DEMIBOLD,
            data_font: &theme::TEXT_MONO,
        }
        .into_paragraphs();

        let obj = if self.hold {
            let mut frame = Frame::left_aligned(
                theme::label_title(),
                self.title,
                SwipeHoldPage::new(paragraphs, theme::BG),
            );
            if let Some(subtitle) = self.subtitle {
                frame = frame.with_subtitle(theme::label_subtitle(), subtitle);
            }
            if self.info_button {
                frame = frame.with_info_button();
            }
            LayoutObj::new(frame)?
        } else if let Some(verb) = self.verb {
            let buttons = Button::cancel_confirm_text(self.verb_cancel, Some(verb));
            let mut frame = Frame::left_aligned(
                theme::label_title(),
                self.title,
                SwipePage::new(paragraphs, buttons, theme::BG).with_cancel_on_first_page(),
            );
            if let Some(subtitle) = self.subtitle {
                frame = frame.with_subtitle(theme::label_subtitle(), subtitle);
            }
            if self.info_button {
                frame = frame.with_info_button();
            }
            LayoutObj::new(frame)?
        } else {
            panic!("Either `hold=true` or `verb=Some(StrBuffer)` must be specified");
        };
        Ok(obj.into())
    }
}

extern "C" fn new_confirm_blob(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let data: Obj = kwargs.get(Qstr::MP_QSTR_data)?;
        let description: Option<StrBuffer> =
            kwargs.get(Qstr::MP_QSTR_description)?.try_into_option()?;
        let extra: Option<StrBuffer> = kwargs.get(Qstr::MP_QSTR_extra)?.try_into_option()?;
        let verb: Option<StrBuffer> = kwargs
            .get(Qstr::MP_QSTR_verb)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let verb_cancel: Option<StrBuffer> = kwargs
            .get(Qstr::MP_QSTR_verb_cancel)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;

        ConfirmBlobParams::new(title, data, description, verb, verb_cancel, hold)
            .with_extra(extra)
            .into_layout()
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_address(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: Option<StrBuffer> =
            kwargs.get(Qstr::MP_QSTR_description)?.try_into_option()?;
        let extra: Option<StrBuffer> = kwargs.get(Qstr::MP_QSTR_extra)?.try_into_option()?;
        let data: Obj = kwargs.get(Qstr::MP_QSTR_data)?;

        let paragraphs = ConfirmBlob {
            description: description.unwrap_or_else(StrBuffer::empty),
            extra: extra.unwrap_or_else(StrBuffer::empty),
            data: data.try_into()?,
            description_font: &theme::TEXT_NORMAL,
            extra_font: &theme::TEXT_DEMIBOLD,
            data_font: &theme::TEXT_MONO,
        }
        .into_paragraphs();

        let buttons = Button::cancel_confirm_text(None, Some("CONFIRM"));
        let obj = LayoutObj::new(
            Frame::left_aligned(
                theme::label_title(),
                title,
                SwipePage::new(paragraphs, buttons, theme::BG)
                    .with_swipe_left()
                    .with_cancel_on_first_page(),
            )
            .with_info_button(),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_properties(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;

        let paragraphs = PropsList::new(
            items,
            &theme::TEXT_DEMIBOLD,
            &theme::TEXT_NORMAL,
            &theme::TEXT_MONO,
        )?;
        let obj = if hold {
            LayoutObj::new(Frame::left_aligned(
                theme::label_title(),
                title,
                SwipeHoldPage::new(paragraphs.into_paragraphs(), theme::BG),
            ))?
        } else {
            let buttons = Button::cancel_confirm_text(None, Some("CONFIRM"));
            LayoutObj::new(Frame::left_aligned(
                theme::label_title(),
                title,
                SwipePage::new(paragraphs.into_paragraphs(), buttons, theme::BG)
                    .with_cancel_on_first_page(),
            ))?
        };
        Ok(obj.into())
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

        let size = match jpeg_info(buffer_func()) {
            Some(info) => info.0,
            _ => return Err(value_error!("Invalid image.")),
        };

        let buttons = Button::cancel_confirm_text(None, Some("CONFIRM"));
        let obj = LayoutObj::new(Frame::centered(
            theme::label_title(),
            title,
            Dialog::new(painter::jpeg_painter(buffer_func, size, 1), buttons),
        ))?;
        Ok(obj.into())
    };

    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_reset_device(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let button: StrBuffer = kwargs.get(Qstr::MP_QSTR_button)?.try_into()?;

        let paragraphs = Paragraphs::new([
            Paragraph::new(
                &theme::TEXT_NORMAL,
                StrBuffer::from(
                    "By continuing you agree\nto Trezor Company's\nterms and conditions.\r",
                ),
            ),
            Paragraph::new(&theme::TEXT_NORMAL, StrBuffer::from("More info at")),
            Paragraph::new(&theme::TEXT_DEMIBOLD, StrBuffer::from("trezor.io/tos")),
        ]);
        let buttons = Button::cancel_confirm(
            Button::with_icon(theme::ICON_CANCEL),
            Button::with_text(button).styled(theme::button_confirm()),
            true,
        );
        let obj = LayoutObj::new(Frame::left_aligned(
            theme::label_title(),
            title,
            Dialog::new(paragraphs, buttons),
        ))?;
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
            let [xtitle, text]: [StrBuffer; 2] = iter_into_array(i)?;
            ad.add_xpub(xtitle, text)?;
        }

        let obj = LayoutObj::new(HorizontalPage::new(ad, theme::BG).with_swipe_right_to_go_back())?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_spending_details(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get_or(Qstr::MP_QSTR_title, "INFORMATION".into())?;
        let account: Option<StrBuffer> = kwargs.get(Qstr::MP_QSTR_account)?.try_into_option()?;
        let fee_rate: Option<StrBuffer> = kwargs.get(Qstr::MP_QSTR_fee_rate)?.try_into_option()?;
        let fee_rate_title: StrBuffer =
            kwargs.get_or(Qstr::MP_QSTR_fee_rate_title, "Fee rate:".into())?;

        let mut paragraphs = ParagraphVecShort::new();
        if let Some(a) = account {
            paragraphs.add(Paragraph::new(
                &theme::TEXT_NORMAL,
                "Sending from account:".into(),
            ));
            paragraphs.add(Paragraph::new(&theme::TEXT_MONO, a));
        }
        if let Some(f) = fee_rate {
            paragraphs.add(Paragraph::new(&theme::TEXT_NORMAL, fee_rate_title));
            paragraphs.add(Paragraph::new(&theme::TEXT_MONO, f));
        }

        let obj = LayoutObj::new(
            Frame::left_aligned(
                theme::label_title(),
                title,
                SwipePage::new(paragraphs.into_paragraphs(), Empty, theme::BG).with_swipe_right(),
            )
            .with_cancel_button(),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_value(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let subtitle: Option<StrBuffer> = kwargs.get(Qstr::MP_QSTR_subtitle)?.try_into_option()?;
        let description: Option<StrBuffer> =
            kwargs.get(Qstr::MP_QSTR_description)?.try_into_option()?;
        let value: Obj = kwargs.get(Qstr::MP_QSTR_value)?;
        let info_button: bool = kwargs.get_or(Qstr::MP_QSTR_info_button, false)?;

        let verb: Option<StrBuffer> = kwargs
            .get(Qstr::MP_QSTR_verb)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let verb_cancel: Option<StrBuffer> = kwargs
            .get(Qstr::MP_QSTR_verb_cancel)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;

        ConfirmBlobParams::new(title, value, description, verb, verb_cancel, hold)
            .with_subtitle(subtitle)
            .with_info_button(info_button)
            .into_layout()
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_total(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;
        let info_button: bool = kwargs.get_or(Qstr::MP_QSTR_info_button, false)?;

        let mut paragraphs = ParagraphVecShort::new();

        for pair in IterBuf::new().try_iterate(items)? {
            let [label, value]: [StrBuffer; 2] = iter_into_array(pair)?;
            paragraphs.add(Paragraph::new(&theme::TEXT_NORMAL, label));
            paragraphs.add(Paragraph::new(&theme::TEXT_MONO, value));
        }

        let mut page = SwipeHoldPage::new(paragraphs.into_paragraphs(), theme::BG);
        if info_button {
            page = page.with_swipe_left();
        }
        let mut frame = Frame::left_aligned(theme::label_title(), title, page);
        if info_button {
            frame = frame.with_info_button();
        }
        let obj = LayoutObj::new(frame)?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_modify_output(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let sign: i32 = kwargs.get(Qstr::MP_QSTR_sign)?.try_into()?;
        let amount_change: StrBuffer = kwargs.get(Qstr::MP_QSTR_amount_change)?.try_into()?;
        let amount_new: StrBuffer = kwargs.get(Qstr::MP_QSTR_amount_new)?.try_into()?;

        let description = if sign < 0 {
            "Decrease amount by:"
        } else {
            "Increase amount by:"
        };

        let paragraphs = Paragraphs::new([
            Paragraph::new(&theme::TEXT_NORMAL, description.into()),
            Paragraph::new(&theme::TEXT_MONO, amount_change),
            Paragraph::new(&theme::TEXT_NORMAL, "New amount:".into()),
            Paragraph::new(&theme::TEXT_MONO, amount_new),
        ]);

        let buttons = Button::cancel_confirm_text(Some("^"), Some("CONTINUE"));
        let obj = LayoutObj::new(Frame::left_aligned(
            theme::label_title(),
            "MODIFY AMOUNT",
            SwipePage::new(paragraphs, buttons, theme::BG),
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_modify_fee(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let sign: i32 = kwargs.get(Qstr::MP_QSTR_sign)?.try_into()?;
        let user_fee_change: StrBuffer = kwargs.get(Qstr::MP_QSTR_user_fee_change)?.try_into()?;
        let total_fee_new: StrBuffer = kwargs.get(Qstr::MP_QSTR_total_fee_new)?.try_into()?;

        let (description, change, total_label) = match sign {
            s if s < 0 => ("Decrease fee by:", user_fee_change, "New transaction fee:"),
            s if s > 0 => ("Increase fee by:", user_fee_change, "New transaction fee:"),
            _ => (
                "Fee did not change.\r",
                StrBuffer::empty(),
                "Transaction fee:",
            ),
        };

        let paragraphs = Paragraphs::new([
            Paragraph::new(&theme::TEXT_NORMAL, description.into()),
            Paragraph::new(&theme::TEXT_MONO, change),
            Paragraph::new(&theme::TEXT_NORMAL, total_label.into()),
            Paragraph::new(&theme::TEXT_MONO, total_fee_new),
        ]);

        let obj = LayoutObj::new(
            Frame::left_aligned(
                theme::label_title(),
                title,
                SwipeHoldPage::new(paragraphs, theme::BG).with_swipe_left(),
            )
            .with_info_button(),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

fn new_show_modal(
    kwargs: &Map,
    icon: BlendedImage,
    button_style: ButtonStyleSheet,
) -> Result<Obj, Error> {
    let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
    let description: StrBuffer = kwargs.get_or(Qstr::MP_QSTR_description, StrBuffer::empty())?;
    let button: StrBuffer = kwargs.get_or(Qstr::MP_QSTR_button, "CONTINUE".into())?;
    let allow_cancel: bool = kwargs.get_or(Qstr::MP_QSTR_allow_cancel, true)?;
    let time_ms: u32 = kwargs.get_or(Qstr::MP_QSTR_time_ms, 0)?;

    let no_buttons = button.as_ref().is_empty();
    let obj = if no_buttons && time_ms == 0 {
        // No buttons and no timer, used when we only want to draw the dialog once and
        // then throw away the layout object.
        LayoutObj::new(IconDialog::new(icon, title, Empty).with_description(description))?.into()
    } else if no_buttons && time_ms > 0 {
        // Timeout, no buttons.
        LayoutObj::new(
            IconDialog::new(
                icon,
                title,
                Timeout::new(time_ms).map(|_| Some(CancelConfirmMsg::Confirmed)),
            )
            .with_description(description),
        )?
        .into()
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
            .with_description(description),
        )?
        .into()
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
            .with_description(description),
        )?
        .into()
    };

    Ok(obj)
}

extern "C" fn new_show_error(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let icon = BlendedImage::new(
            theme::IMAGE_BG_CIRCLE,
            theme::IMAGE_FG_ERROR,
            theme::ERROR_COLOR,
            theme::FG,
            theme::BG,
        );
        new_show_modal(kwargs, icon, theme::button_default())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_fido(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let app_name: StrBuffer = kwargs.get(Qstr::MP_QSTR_app_name)?.try_into()?;
        let icon: Option<StrBuffer> = kwargs.get(Qstr::MP_QSTR_icon_name)?.try_into_option()?;
        let accounts: Gc<List> = kwargs.get(Qstr::MP_QSTR_accounts)?.try_into()?;

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
            Button::with_text("CONFIRM").styled(theme::button_confirm()),
            true,
        );

        let fido_page = FidoConfirm::new(app_name, get_page, page_count, icon, controls);

        let obj = LayoutObj::new(Frame::centered(theme::label_title(), title, fido_page))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_warning(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let icon = BlendedImage::new(
            theme::IMAGE_BG_OCTAGON,
            theme::IMAGE_FG_WARN,
            theme::WARN_COLOR,
            theme::FG,
            theme::BG,
        );
        new_show_modal(kwargs, icon, theme::button_reset())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_success(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let icon = BlendedImage::new(
            theme::IMAGE_BG_CIRCLE,
            theme::IMAGE_FG_SUCCESS,
            theme::SUCCESS_COLOR,
            theme::FG,
            theme::BG,
        );
        new_show_modal(kwargs, icon, theme::button_confirm())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_info(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let icon = BlendedImage::new(
            theme::IMAGE_BG_CIRCLE,
            theme::IMAGE_FG_INFO,
            theme::INFO_COLOR,
            theme::FG,
            theme::BG,
        );
        new_show_modal(kwargs, icon, theme::button_info())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_mismatch() -> Obj {
    let block = move || {
        let title: StrBuffer = "Address mismatch?".into();
        let description: StrBuffer = "Please contact Trezor support at".into();
        let url: StrBuffer = "trezor.io/support".into();
        let button = "QUIT";

        let icon = BlendedImage::new(
            theme::IMAGE_BG_OCTAGON,
            theme::IMAGE_FG_WARN,
            theme::WARN_COLOR,
            theme::FG,
            theme::BG,
        );
        let obj = LayoutObj::new(
            IconDialog::new(
                icon,
                title,
                Button::cancel_confirm(
                    Button::with_icon(theme::ICON_BACK),
                    Button::with_text(button).styled(theme::button_reset()),
                    true,
                ),
            )
            .with_description(description)
            .with_text(&theme::TEXT_DEMIBOLD, url),
        )?;

        Ok(obj.into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn new_show_simple(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: Option<StrBuffer> = kwargs.get(Qstr::MP_QSTR_title)?.try_into_option()?;
        let description: StrBuffer =
            kwargs.get_or(Qstr::MP_QSTR_description, StrBuffer::empty())?;
        let button: StrBuffer = kwargs.get_or(Qstr::MP_QSTR_button, StrBuffer::empty())?;

        let obj = if let Some(t) = title {
            LayoutObj::new(Frame::left_aligned(
                theme::label_title(),
                t,
                Dialog::new(
                    Paragraphs::new([Paragraph::new(&theme::TEXT_NORMAL, description)]),
                    theme::button_bar(Button::with_text(button).map(|msg| {
                        (matches!(msg, ButtonMsg::Clicked)).then(|| CancelConfirmMsg::Confirmed)
                    })),
                ),
            ))?
            .into()
        } else if !button.is_empty() {
            LayoutObj::new(Border::new(
                theme::borders(),
                Dialog::new(
                    Paragraphs::new([Paragraph::new(&theme::TEXT_NORMAL, description)]),
                    theme::button_bar(Button::with_text(button).map(|msg| {
                        (matches!(msg, ButtonMsg::Clicked)).then(|| CancelConfirmMsg::Confirmed)
                    })),
                ),
            ))?
            .into()
        } else {
            LayoutObj::new(Border::new(
                theme::borders(),
                Dialog::new(
                    Paragraphs::new(
                        [Paragraph::new(&theme::TEXT_DEMIBOLD, description).centered()],
                    ),
                    Empty,
                ),
            ))?
            .into()
        };

        Ok(obj)
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_with_info(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let button: StrBuffer = kwargs.get(Qstr::MP_QSTR_button)?.try_into()?;
        let info_button: StrBuffer = kwargs.get(Qstr::MP_QSTR_info_button)?.try_into()?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;

        let mut paragraphs = ParagraphVecShort::new();

        for para in IterBuf::new().try_iterate(items)? {
            let [font, text]: [Obj; 2] = iter_into_array(para)?;
            let style: &TextStyle = theme::textstyle_number(font.try_into()?);
            let text: StrBuffer = text.try_into()?;
            paragraphs.add(Paragraph::new(style, text));
            if paragraphs.is_full() {
                break;
            }
        }

        let buttons = Button::cancel_info_confirm(button, info_button);

        let obj = LayoutObj::new(Frame::left_aligned(
            theme::label_title(),
            title,
            Dialog::new(paragraphs.into_paragraphs(), buttons),
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_more(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let button: StrBuffer = kwargs.get(Qstr::MP_QSTR_button)?.try_into()?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;

        let mut paragraphs = ParagraphVecLong::new();

        for para in IterBuf::new().try_iterate(items)? {
            let [font, text]: [Obj; 2] = iter_into_array(para)?;
            let style: &TextStyle = theme::textstyle_number(font.try_into()?);
            let text: StrBuffer = text.try_into()?;
            paragraphs.add(Paragraph::new(style, text));
        }

        let button =
            theme::button_bar(Button::with_text(button).map(|msg| {
                (matches!(msg, ButtonMsg::Clicked)).then(|| CancelConfirmMsg::Confirmed)
            }));

        let obj = LayoutObj::new(Frame::left_aligned(
            theme::label_title(),
            title,
            SwipePage::new(paragraphs.into_paragraphs(), button, theme::BG).with_back_button(),
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
            Paragraph::new(&theme::TEXT_NORMAL, "Max rounds".into()),
            Paragraph::new(&theme::TEXT_MONO, max_rounds),
            Paragraph::new(&theme::TEXT_NORMAL, "Max mining fee".into()),
            Paragraph::new(&theme::TEXT_MONO, max_feerate),
        ]);

        let obj = LayoutObj::new(Frame::left_aligned(
            theme::label_title(),
            "AUTHORIZE COINJOIN",
            SwipeHoldPage::new(paragraphs, theme::BG),
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_pin(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let prompt: StrBuffer = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let subprompt: StrBuffer = kwargs.get(Qstr::MP_QSTR_subprompt)?.try_into()?;
        let allow_cancel: bool = kwargs.get_or(Qstr::MP_QSTR_allow_cancel, true)?;
        let warning: bool = kwargs.get_or(Qstr::MP_QSTR_wrong_pin, false)?;
        let warning = if warning {
            Some("Wrong PIN".into())
        } else {
            None
        };
        let obj = LayoutObj::new(PinKeyboard::new(prompt, subprompt, warning, allow_cancel))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_passphrase(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let _prompt: StrBuffer = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let _max_len: u32 = kwargs.get(Qstr::MP_QSTR_max_len)?.try_into()?;
        let obj = LayoutObj::new(PassphraseKeyboard::new())?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_bip39(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let prompt: StrBuffer = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let obj = LayoutObj::new(MnemonicKeyboard::new(Bip39Input::new(), prompt))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_slip39(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let prompt: StrBuffer = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let obj = LayoutObj::new(MnemonicKeyboard::new(Slip39Input::new(), prompt))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_select_word(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: StrBuffer = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let words_iterable: Obj = kwargs.get(Qstr::MP_QSTR_words)?;
        let words: [StrBuffer; 3] = iter_into_array(words_iterable)?;

        let paragraphs = Paragraphs::new([Paragraph::new(&theme::TEXT_DEMIBOLD, description)]);
        let buttons = Button::select_word(words);

        let obj = LayoutObj::new(Frame::left_aligned(
            theme::label_title(),
            title,
            SwipePage::new(paragraphs, buttons, theme::BG),
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_share_words(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let pages: Obj = kwargs.get(Qstr::MP_QSTR_pages)?;

        let mut paragraphs = ParagraphVecLong::new();
        for page in IterBuf::new().try_iterate(pages)? {
            let text: StrBuffer = page.try_into()?;
            paragraphs.add(Paragraph::new(&theme::TEXT_MONO, text).break_after());
        }

        let obj = LayoutObj::new(Frame::left_aligned(
            theme::label_title(),
            title,
            SwipeHoldPage::without_cancel(paragraphs.into_paragraphs(), theme::BG),
        ))?;
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
        let description_callback: Obj = kwargs.get(Qstr::MP_QSTR_description)?;
        assert!(description_callback != Obj::const_none());

        let callback = move |i: u32| {
            StrBuffer::try_from(
                description_callback
                    .call_with_n_args(&[i.try_into().unwrap()])
                    .unwrap(),
            )
            .unwrap()
        };

        let obj = LayoutObj::new(Frame::left_aligned(
            theme::label_title(),
            title,
            NumberInputDialog::new(min_count, max_count, count, callback),
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_checklist(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let button: StrBuffer = kwargs.get(Qstr::MP_QSTR_button)?.try_into()?;
        let active: usize = kwargs.get(Qstr::MP_QSTR_active)?.try_into()?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;

        let mut paragraphs = ParagraphVecLong::new();
        for (i, item) in IterBuf::new().try_iterate(items)?.enumerate() {
            let style = match i.cmp(&active) {
                Ordering::Less => &theme::TEXT_CHECKLIST_DONE,
                Ordering::Equal => &theme::TEXT_CHECKLIST_SELECTED,
                Ordering::Greater => &theme::TEXT_CHECKLIST_DEFAULT,
            };
            let text: StrBuffer = item.try_into()?;
            paragraphs.add(Paragraph::new(style, text));
        }

        let obj = LayoutObj::new(Frame::left_aligned(
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
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_recovery(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: StrBuffer = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let button: StrBuffer = kwargs.get(Qstr::MP_QSTR_button)?.try_into()?;
        let dry_run: bool = kwargs.get(Qstr::MP_QSTR_dry_run)?.try_into()?;
        let info_button: bool = kwargs.get_or(Qstr::MP_QSTR_info_button, false)?;

        let paragraphs = Paragraphs::new([
            Paragraph::new(&theme::TEXT_DEMIBOLD, title).centered(),
            Paragraph::new(&theme::TEXT_NORMAL_OFF_WHITE, description).centered(),
        ])
        .with_spacing(theme::RECOVERY_SPACING);

        let notification = if dry_run {
            "SEED CHECK"
        } else {
            "RECOVERY MODE"
        };

        let obj = if info_button {
            LayoutObj::new(NotificationFrame::new(
                notification,
                Dialog::new(
                    paragraphs,
                    Button::cancel_info_confirm("CONTINUE", "MORE INFO"),
                ),
            ))?
        } else {
            LayoutObj::new(NotificationFrame::new(
                notification,
                Dialog::new(paragraphs, Button::cancel_confirm_text(None, Some(button))),
            ))?
        };
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_select_word_count(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let dry_run: bool = kwargs.get(Qstr::MP_QSTR_dry_run)?.try_into()?;
        let title = if dry_run {
            "SEED CHECK"
        } else {
            "WALLET RECOVERY"
        };

        let paragraphs = Paragraphs::new(
            Paragraph::new(
                &theme::TEXT_DEMIBOLD,
                StrBuffer::from("Select number of words in your recovery seed."),
            )
            .centered(),
        );

        let obj = LayoutObj::new(Frame::left_aligned(
            theme::label_title(),
            title,
            Dialog::new(paragraphs, SelectWordCount::new()),
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
        let lines: [StrBuffer; 4] = iter_into_array(lines_iterable)?;

        let obj = LayoutObj::new(IconDialog::new_shares(
            lines,
            theme::button_bar(Button::with_text("CONTINUE").map(|msg| {
                (matches!(msg, ButtonMsg::Clicked)).then(|| CancelConfirmMsg::Confirmed)
            })),
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_remaining_shares(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let pages_iterable: Obj = kwargs.get(Qstr::MP_QSTR_pages)?;

        let mut paragraphs = ParagraphVecLong::new();
        for page in IterBuf::new().try_iterate(pages_iterable)? {
            let [title, description]: [StrBuffer; 2] = iter_into_array(page)?;
            paragraphs
                .add(Paragraph::new(&theme::TEXT_DEMIBOLD, title))
                .add(Paragraph::new(&theme::TEXT_NORMAL, description).break_after());
        }

        let obj = LayoutObj::new(Frame::left_aligned(
            theme::label_title(),
            "REMAINING SHARES",
            SwipePage::new(
                paragraphs.into_paragraphs(),
                theme::button_bar(Button::with_text("CONTINUE").map(|msg| {
                    (matches!(msg, ButtonMsg::Clicked)).then(|| CancelConfirmMsg::Confirmed)
                })),
                theme::BG,
            ),
        ))?;
        Ok(obj.into())
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

extern "C" fn new_show_progress_coinjoin(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let indeterminate: bool = kwargs.get_or(Qstr::MP_QSTR_indeterminate, false)?;
        let time_ms: u32 = kwargs.get_or(Qstr::MP_QSTR_time_ms, 0)?;
        let skip_first_paint: bool = kwargs.get_or(Qstr::MP_QSTR_skip_first_paint, false)?;

        // The second type parameter is actually not used in `new()` but we need to
        // provide it.
        let progress = CoinJoinProgress::<_, Never>::new(title, indeterminate);
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
            .unwrap_or_else(|| constant::MODEL_NAME.into());
        let notification: Option<StrBuffer> =
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
        let label: StrBuffer = kwargs
            .get(Qstr::MP_QSTR_label)?
            .try_into_option()?
            .unwrap_or_else(|| constant::MODEL_NAME.into());
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

extern "C" fn draw_welcome_screen() -> Obj {
    // No need of util::try_or_raise, this does not allocate
    let mut screen = WelcomeScreen::new();
    screen.place(constant::screen());
    display::sync();
    screen.paint();
    display::set_backlight(theme::BACKLIGHT_NORMAL);
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

    /// def jpeg_info(data: bytes) -> tuple[int, int, int]:
    ///     """Get JPEG image dimensions (width: int, height: int, mcu_height: int)."""
    Qstr::MP_QSTR_jpeg_info => obj_fn_1!(upy_jpeg_info).as_obj(),

    /// def jpeg_test(data: bytes) -> bool:
    ///     """Test JPEG image."""
    Qstr::MP_QSTR_jpeg_test => obj_fn_1!(upy_jpeg_test).as_obj(),

    /// def confirm_action(
    ///     *,
    ///     title: str,
    ///     action: str | None,
    ///     description: str | None,
    ///     verb: str | None = None,
    ///     verb_cancel: str | None = None,
    ///     hold: bool = False,
    ///     hold_danger: bool = False,
    ///     reverse: bool = False,
    /// ) -> object:
    ///     """Confirm action."""
    Qstr::MP_QSTR_confirm_action => obj_fn_kw!(0, new_confirm_action).as_obj(),

    /// def confirm_emphasized(
    ///     *,
    ///     title: str,
    ///     items: Iterable[str | tuple[bool, str]],
    ///     verb: str | None = None,
    /// ) -> object:
    ///     """Confirm formatted text that has been pre-split in python. For tuples
    ///     the first component is a bool indicating whether this part is emphasized."""
    Qstr::MP_QSTR_confirm_emphasized => obj_fn_kw!(0, new_confirm_emphasized).as_obj(),

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
    ///     verb: str | None = None,
    ///     verb_cancel: str | None = None,
    ///     hold: bool = False,
    /// ) -> object:
    ///     """Confirm byte sequence data."""
    Qstr::MP_QSTR_confirm_blob => obj_fn_kw!(0, new_confirm_blob).as_obj(),

    /// def confirm_address(
    ///     *,
    ///     title: str,
    ///     data: str | bytes,
    ///     description: str | None,
    ///     extra: str | None,
    /// ) -> object:
    ///     """Confirm address. Similar to `confirm_blob` but has corner info button
    ///     and allows left swipe which does the same thing as the button."""
    Qstr::MP_QSTR_confirm_address => obj_fn_kw!(0, new_confirm_address).as_obj(),

    /// def confirm_properties(
    ///     *,
    ///     title: str,
    ///     items: list[tuple[str | None, str | bytes | None, bool]],
    ///     hold: bool = False,
    /// ) -> object:
    ///     """Confirm list of key-value pairs. The third component in the tuple should be True if
    ///     the value is to be rendered as binary with monospace font, False otherwise."""
    Qstr::MP_QSTR_confirm_properties => obj_fn_kw!(0, new_confirm_properties).as_obj(),

    /// def confirm_reset_device(
    ///     *,
    ///     title: str,
    ///     button: str,
    /// ) -> object:
    ///     """Confirm TOS before device setup."""
    Qstr::MP_QSTR_confirm_reset_device => obj_fn_kw!(0, new_confirm_reset_device).as_obj(),

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

    /// def show_spending_details(
    ///     *,
    ///     title: str = "INFORMATION",
    ///     account: str | None,
    ///     fee_rate: str | None,
    ///     fee_rate_title: str = "Fee rate:",
    /// ) -> object:
    ///     """Show metadata when for outgoing transaction."""
    Qstr::MP_QSTR_show_spending_details => obj_fn_kw!(0, new_show_spending_details).as_obj(),

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
    /// ) -> object:
    ///     """Confirm value. Merge of confirm_total and confirm_output."""
    Qstr::MP_QSTR_confirm_value => obj_fn_kw!(0, new_confirm_value).as_obj(),

    /// def confirm_total(
    ///     *,
    ///     title: str,
    ///     items: list[tuple[str, str]],
    ///     info_button: bool = False,
    /// ) -> object:
    ///     """Transaction summary. Always hold to confirm."""
    Qstr::MP_QSTR_confirm_total => obj_fn_kw!(0, new_confirm_total).as_obj(),

    /// def confirm_modify_output(
    ///     *,
    ///     address: str,  # ignored
    ///     sign: int,
    ///     amount_change: str,
    ///     amount_new: str,
    /// ) -> object:
    ///     """Decrease or increase amount for given address."""
    Qstr::MP_QSTR_confirm_modify_output => obj_fn_kw!(0, new_confirm_modify_output).as_obj(),

    /// def confirm_modify_fee(
    ///     *,
    ///     title: str,
    ///     sign: int,
    ///     user_fee_change: str,
    ///     total_fee_new: str,
    ///     fee_rate_amount: str | None,  # ignored
    /// ) -> object:
    ///     """Decrease or increase transaction fee."""
    Qstr::MP_QSTR_confirm_modify_fee => obj_fn_kw!(0, new_confirm_modify_fee).as_obj(),

    /// def confirm_fido(
    ///     *,
    ///     title: str,
    ///     app_name: str,
    ///     icon_name: str | None,
    ///     accounts: list[str | None],
    /// ) -> int | object:
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
    /// ) -> object:
    ///     """Error modal. No buttons shown when `button` is empty string."""
    Qstr::MP_QSTR_show_error => obj_fn_kw!(0, new_show_error).as_obj(),

    /// def show_warning(
    ///     *,
    ///     title: str,
    ///     button: str = "CONTINUE",
    ///     description: str = "",
    ///     allow_cancel: bool = False,
    ///     time_ms: int = 0,
    /// ) -> object:
    ///     """Warning modal. No buttons shown when `button` is empty string."""
    Qstr::MP_QSTR_show_warning => obj_fn_kw!(0, new_show_warning).as_obj(),

    /// def show_success(
    ///     *,
    ///     title: str,
    ///     button: str = "CONTINUE",
    ///     description: str = "",
    ///     allow_cancel: bool = False,
    ///     time_ms: int = 0,
    /// ) -> object:
    ///     """Success modal. No buttons shown when `button` is empty string."""
    Qstr::MP_QSTR_show_success => obj_fn_kw!(0, new_show_success).as_obj(),

    /// def show_info(
    ///     *,
    ///     title: str,
    ///     button: str = "CONTINUE",
    ///     description: str = "",
    ///     allow_cancel: bool = False,
    ///     time_ms: int = 0,
    /// ) -> object:
    ///     """Info modal. No buttons shown when `button` is empty string."""
    Qstr::MP_QSTR_show_info => obj_fn_kw!(0, new_show_info).as_obj(),

    /// def show_mismatch() -> object:
    ///     """Warning modal, receiving address mismatch."""
    Qstr::MP_QSTR_show_mismatch => obj_fn_0!(new_show_mismatch).as_obj(),

    /// def show_simple(
    ///     *,
    ///     title: str | None,
    ///     description: str = "",
    ///     button: str = "",
    /// ) -> object:
    ///     """Simple dialog with text and one button."""
    Qstr::MP_QSTR_show_simple => obj_fn_kw!(0, new_show_simple).as_obj(),

    /// def confirm_with_info(
    ///     *,
    ///     title: str,
    ///     button: str,
    ///     info_button: str,
    ///     items: Iterable[tuple[int, str]],
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
    ///     allow_cancel: bool = True,
    ///     wrong_pin: bool = False,
    /// ) -> str | object:
    ///     """Request pin on device."""
    Qstr::MP_QSTR_request_pin => obj_fn_kw!(0, new_request_pin).as_obj(),

    /// def request_passphrase(
    ///     *,
    ///     prompt: str,
    ///     max_len: int,
    /// ) -> str | object:
    ///     """Passphrase input keyboard."""
    Qstr::MP_QSTR_request_passphrase => obj_fn_kw!(0, new_request_passphrase).as_obj(),

    /// def request_bip39(
    ///     *,
    ///     prompt: str,
    /// ) -> str:
    ///     """BIP39 word input keyboard."""
    Qstr::MP_QSTR_request_bip39 => obj_fn_kw!(0, new_request_bip39).as_obj(),

    /// def request_slip39(
    ///     *,
    ///     prompt: str,
    /// ) -> str:
    ///     """SLIP39 word input keyboard."""
    Qstr::MP_QSTR_request_slip39 => obj_fn_kw!(0, new_request_slip39).as_obj(),

    /// def select_word(
    ///     *,
    ///     title: str,
    ///     description: str,
    ///     words: Iterable[str],
    /// ) -> int:
    ///     """Select mnemonic word from three possibilities - seed check after backup. The
    ///    iterable must be of exact size. Returns index in range `0..3`."""
    Qstr::MP_QSTR_select_word => obj_fn_kw!(0, new_select_word).as_obj(),

    /// def show_share_words(
    ///     *,
    ///     title: str,
    ///     pages: Iterable[str],
    /// ) -> object:
    ///     """Show mnemonic for backup. Expects the words pre-divided into individual pages."""
    Qstr::MP_QSTR_show_share_words => obj_fn_kw!(0, new_show_share_words).as_obj(),

    /// def request_number(
    ///     *,
    ///     title: str,
    ///     count: int,
    ///     min_count: int,
    ///     max_count: int,
    ///     description: Callable[[int], str] | None = None,
    /// ) -> object:
    ///     """Number input with + and - buttons, description, and info button."""
    Qstr::MP_QSTR_request_number => obj_fn_kw!(0, new_request_number).as_obj(),

    /// def show_checklist(
    ///     *,
    ///     title: str,
    ///     items: Iterable[str],
    ///     active: int,
    ///     button: str,
    /// ) -> object:
    ///     """Checklist of backup steps. Active index is highlighted, previous items have check
    ///    mark next to them."""
    Qstr::MP_QSTR_show_checklist => obj_fn_kw!(0, new_show_checklist).as_obj(),

    /// def confirm_recovery(
    ///     *,
    ///     title: str,
    ///     description: str,
    ///     button: str,
    ///     dry_run: bool,
    ///     info_button: bool = False,
    /// ) -> object:
    ///     """Device recovery homescreen."""
    Qstr::MP_QSTR_confirm_recovery => obj_fn_kw!(0, new_confirm_recovery).as_obj(),

    /// def select_word_count(
    ///     *,
    ///     dry_run: bool,
    /// ) -> int | str:  # TT returns int
    ///     """Select mnemonic word count from (12, 18, 20, 24, 33)."""
    Qstr::MP_QSTR_select_word_count => obj_fn_kw!(0, new_select_word_count).as_obj(),

    /// def show_group_share_success(
    ///     *,
    ///     lines: Iterable[str]
    /// ) -> int:
    ///     """Shown after successfully finishing a group."""
    Qstr::MP_QSTR_show_group_share_success => obj_fn_kw!(0, new_show_group_share_success).as_obj(),

    /// def show_remaining_shares(
    ///     *,
    ///     pages: Iterable[tuple[str, str]],
    /// ) -> int:
    ///     """Shows SLIP39 state after info button is pressed on `confirm_recovery`."""
    Qstr::MP_QSTR_show_remaining_shares => obj_fn_kw!(0, new_show_remaining_shares).as_obj(),

    /// def show_progress(
    ///     *,
    ///     title: str,
    ///     indeterminate: bool = False,
    ///     description: str = "",
    /// ) -> object:
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
    /// ) -> object:
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
    /// ) -> CANCELLED:
    ///     """Idle homescreen."""
    Qstr::MP_QSTR_show_homescreen => obj_fn_kw!(0, new_show_homescreen).as_obj(),

    /// def show_lockscreen(
    ///     *,
    ///     label: str | None,
    ///     bootscreen: bool,
    ///     skip_first_paint: bool,
    /// ) -> CANCELLED:
    ///     """Homescreen for locked device."""
    Qstr::MP_QSTR_show_lockscreen => obj_fn_kw!(0, new_show_lockscreen).as_obj(),

    /// def draw_welcome_screen() -> None:
    ///     """Show logo icon with the model name at the bottom and return."""
    Qstr::MP_QSTR_draw_welcome_screen => obj_fn_0!(draw_welcome_screen).as_obj(),
};

#[cfg(test)]
mod tests {
    use serde_json;

    use crate::{
        trace::tests::trace,
        ui::{component::text::op::OpTextLayout, geometry::Rect, model_tt::constant},
    };

    use super::*;

    const SCREEN: Rect = constant::screen().inset(theme::borders());

    #[test]
    fn trace_example_layout() {
        let buttons =
            Button::cancel_confirm(Button::with_text("Left"), Button::with_text("Right"), false);

        let ops = OpTextLayout::new(theme::TEXT_NORMAL)
            .text_normal("Testing text layout, with some text, and some more text. And ")
            .text_bold("parameters!");
        let formatted = FormattedText::new(ops);
        let mut layout = Dialog::new(formatted, buttons);
        layout.place(SCREEN);

        let expected = serde_json::json!({
            "component": "Dialog",
            "content": {
                "component": "FormattedText",
                "text": ["Testing text layout, with", "\n", "some text, and some", "\n",
                "more text. And ", "paramet", "-", "\n", "ers!"],
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
