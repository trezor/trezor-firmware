use core::{cmp::Ordering, convert::TryInto};

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
    strutil::{StringType, TString},
    translations::TR,
    trezorhal::model,
    ui::{
        component::{
            base::ComponentExt,
            connect::Connect,
            image::BlendedImage,
            jpeg::{ImageBuffer, Jpeg},
            paginated::{PageMsg, Paginate},
            placed::GridPlaced,
            text::{
                op::OpTextLayout,
                paragraphs::{
                    Checklist, Paragraph, ParagraphSource, ParagraphVecLong, ParagraphVecShort,
                    Paragraphs, VecExt,
                },
                TextStyle,
            },
            Border, Component, Empty, FormattedText, Label, Never, Qr, Timeout,
        },
        display::{tjpgd::jpeg_info, Icon},
        geometry,
        layout::{
            obj::{ComponentMsgObj, LayoutObj},
            result::{CANCELLED, CONFIRMED, INFO},
            util::{upy_disable_animation, ConfirmBlob, PropsList},
        },
        model_mercury::component::check_homescreen_format,
    },
};

use super::{
    component::{
        AddressDetails, Bip39Input, Button, ButtonMsg, ButtonPage, ButtonStyleSheet,
        CancelConfirmMsg, CancelInfoConfirmMsg, CoinJoinProgress, Dialog, DialogMsg, FidoConfirm,
        FidoMsg, Frame, FrameMsg, Homescreen, HomescreenMsg, IconDialog, Lockscreen, MnemonicInput,
        MnemonicKeyboard, MnemonicKeyboardMsg, NumberInputDialog, NumberInputDialogMsg,
        PassphraseKeyboard, PassphraseKeyboardMsg, PinKeyboard, PinKeyboardMsg, Progress,
        SelectWordCount, SelectWordCountMsg, SelectWordMsg, SimplePage, Slip39Input, VerticalMenu,
        VerticalMenuChoiceMsg,
    },
    theme,
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

impl TryFrom<VerticalMenuChoiceMsg> for Obj {
    type Error = Error;

    fn try_from(value: VerticalMenuChoiceMsg) -> Result<Self, Self::Error> {
        match value {
            VerticalMenuChoiceMsg::Selected(i) => i.try_into(),
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
            MnemonicKeyboardMsg::Previous => "".try_into(),
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

impl<T> ComponentMsgObj for VerticalMenu<T>
where
    T: AsRef<str>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            VerticalMenuChoiceMsg::Selected(i) => i.try_into(),
        }
    }
}

impl<T, U> ComponentMsgObj for ButtonPage<T, U>
where
    T: Component + Paginate,
    U: AsRef<str> + From<&'static str>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            PageMsg::Content(_) => Err(Error::TypeError),
            PageMsg::Confirmed => Ok(CONFIRMED.as_obj()),
            PageMsg::Cancelled => Ok(CANCELLED.as_obj()),
            PageMsg::SwipeLeft => Ok(INFO.as_obj()),
            PageMsg::SwipeRight => Ok(CANCELLED.as_obj()),
        }
    }
}

impl ComponentMsgObj for Jpeg {
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

impl<T> ComponentMsgObj for SimplePage<T>
where
    T: ComponentMsgObj + Paginate,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            PageMsg::Content(inner_msg) => Ok(self.inner().msg_try_into_obj(inner_msg)?),
            PageMsg::Cancelled => Ok(CANCELLED.as_obj()),
            _ => Err(Error::TypeError),
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

impl<T> ComponentMsgObj for super::component::bl_confirm::Confirm<T>
where
    T: AsRef<str>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            super::component::bl_confirm::ConfirmMsg::Cancel => Ok(CANCELLED.as_obj()),
            super::component::bl_confirm::ConfirmMsg::Confirm => Ok(CONFIRMED.as_obj()),
        }
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

        let mut page = if hold {
            ButtonPage::new(paragraphs, theme::BG).with_hold()?
        } else {
            ButtonPage::new(paragraphs, theme::BG).with_cancel_confirm(verb_cancel, verb)
        };
        if hold && hold_danger {
            page = page.with_confirm_style(theme::button_danger())
        }
        let obj = LayoutObj::new(Frame::left_aligned(title, page))?;
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
                let [emphasis, text]: [Obj; 2] = util::iter_into_array(item)?;
                let text: StrBuffer = text.try_into()?;
                if emphasis.try_into()? {
                    ops = ops.text_demibold(text);
                } else {
                    ops = ops.text_normal(text);
                }
            }
        }

        let obj = LayoutObj::new(Frame::left_aligned(
            title,
            ButtonPage::new(FormattedText::new(ops).vertically_centered(), theme::BG)
                .with_cancel_confirm(None, verb),
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
    chunkify: bool,
    text_mono: bool,
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
            chunkify: false,
            text_mono: true,
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

    fn with_chunkify(mut self, chunkify: bool) -> Self {
        self.chunkify = chunkify;
        self
    }

    fn with_text_mono(mut self, text_mono: bool) -> Self {
        self.text_mono = text_mono;
        self
    }

    fn into_layout(self) -> Result<Obj, Error> {
        let paragraphs = ConfirmBlob {
            description: self.description.unwrap_or_else(StrBuffer::empty),
            extra: self.extra.unwrap_or_else(StrBuffer::empty),
            data: self.data.try_into()?,
            description_font: &theme::TEXT_NORMAL,
            extra_font: &theme::TEXT_DEMIBOLD,
            data_font: if self.chunkify {
                let data: StrBuffer = self.data.try_into()?;
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
        let mut frame = Frame::left_aligned(self.title, page);
        if let Some(subtitle) = self.subtitle {
            frame = frame.with_subtitle(subtitle);
        }
        if self.info_button {
            frame = frame.with_info_button();
        }
        let obj = LayoutObj::new(frame)?;
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
        let chunkify: bool = kwargs.get_or(Qstr::MP_QSTR_chunkify, false)?;

        ConfirmBlobParams::new(title, data, description, verb, verb_cancel, hold)
            .with_extra(extra)
            .with_chunkify(chunkify)
            .into_layout()
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_address(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: Option<StrBuffer> =
            kwargs.get(Qstr::MP_QSTR_description)?.try_into_option()?;
        let verb: StrBuffer =
            kwargs.get_or(Qstr::MP_QSTR_verb, TR::buttons__confirm.try_into()?)?;
        let extra: Option<StrBuffer> = kwargs.get(Qstr::MP_QSTR_extra)?.try_into_option()?;
        let data: Obj = kwargs.get(Qstr::MP_QSTR_data)?;
        let chunkify: bool = kwargs.get_or(Qstr::MP_QSTR_chunkify, false)?;

        let data_style = if chunkify {
            let address: StrBuffer = data.try_into()?;
            theme::get_chunkified_text_style(address.len())
        } else {
            &theme::TEXT_MONO
        };

        let paragraphs = ConfirmBlob {
            description: description.unwrap_or_else(StrBuffer::empty),
            extra: extra.unwrap_or_else(StrBuffer::empty),
            data: data.try_into()?,
            description_font: &theme::TEXT_NORMAL,
            extra_font: &theme::TEXT_DEMIBOLD,
            data_font: data_style,
        }
        .into_paragraphs();

        let obj = LayoutObj::new(
            Frame::left_aligned(
                title,
                ButtonPage::new(paragraphs, theme::BG)
                    .with_swipe_left()
                    .with_cancel_confirm(None, Some(verb)),
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
            &theme::TEXT_NORMAL,
            &theme::TEXT_MONO,
            &theme::TEXT_MONO,
        )?;
        let page: ButtonPage<_, StrBuffer> = if hold {
            ButtonPage::new(paragraphs.into_paragraphs(), theme::BG).with_hold()?
        } else {
            ButtonPage::new(paragraphs.into_paragraphs(), theme::BG)
                .with_cancel_confirm(None, Some(TR::buttons__confirm.try_into()?))
        };
        let obj = LayoutObj::new(Frame::left_aligned(title, page))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_homescreen(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let image: Obj = kwargs.get(Qstr::MP_QSTR_image)?;

        let mut jpeg = unwrap!(ImageBuffer::from_object(image));

        if jpeg.is_empty() {
            // Incoming data may be empty, meaning we should
            // display default homescreen image.
            jpeg = ImageBuffer::from_slice(theme::IMAGE_HOMESCREEN);
        }

        if let None = jpeg_info(jpeg.data()) {
            return Err(value_error!("Invalid image."));
        };

        let tr_change: StrBuffer = TR::buttons__change.try_into()?;
        let buttons = Button::cancel_confirm_text(None, Some(tr_change));
        let obj = LayoutObj::new(Frame::centered(
            title,
            Dialog::new(Jpeg::new(jpeg, 1), buttons),
        ))?;
        Ok(obj.into())
    };

    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_reset_device(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let button: StrBuffer = kwargs.get(Qstr::MP_QSTR_button)?.try_into()?;

        let par_array: [Paragraph<StrBuffer>; 3] = [
            Paragraph::new(&theme::TEXT_NORMAL, TR::reset__by_continuing.try_into()?)
                .with_bottom_padding(17), // simulating a carriage return
            Paragraph::new(&theme::TEXT_NORMAL, TR::reset__more_info_at.try_into()?),
            Paragraph::new(&theme::TEXT_DEMIBOLD, TR::reset__tos_link.try_into()?),
        ];
        let paragraphs = Paragraphs::new(par_array);
        let buttons = Button::cancel_confirm(
            Button::with_icon(theme::ICON_CANCEL),
            Button::with_text(button).styled(theme::button_confirm()),
            true,
        );
        let obj = LayoutObj::new(Frame::left_aligned(title, Dialog::new(paragraphs, buttons)))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_address_details(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let qr_title: StrBuffer = kwargs.get(Qstr::MP_QSTR_qr_title)?.try_into()?;
        let details_title: StrBuffer = kwargs.get(Qstr::MP_QSTR_details_title)?.try_into()?;
        let address: StrBuffer = kwargs.get(Qstr::MP_QSTR_address)?.try_into()?;
        let case_sensitive: bool = kwargs.get(Qstr::MP_QSTR_case_sensitive)?.try_into()?;
        let account: Option<StrBuffer> = kwargs.get(Qstr::MP_QSTR_account)?.try_into_option()?;
        let path: Option<StrBuffer> = kwargs.get(Qstr::MP_QSTR_path)?.try_into_option()?;

        let xpubs: Obj = kwargs.get(Qstr::MP_QSTR_xpubs)?;

        let mut ad = AddressDetails::new(
            qr_title,
            address,
            case_sensitive,
            details_title,
            account,
            path,
        )?;

        for i in IterBuf::new().try_iterate(xpubs)? {
            let [xtitle, text]: [StrBuffer; 2] = util::iter_into_array(i)?;
            ad.add_xpub(xtitle, text)?;
        }

        let obj =
            LayoutObj::new(SimplePage::horizontal(ad, theme::BG).with_swipe_right_to_go_back())?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_info_with_cancel(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;
        let horizontal: bool = kwargs.get_or(Qstr::MP_QSTR_horizontal, false)?;
        let chunkify: bool = kwargs.get_or(Qstr::MP_QSTR_chunkify, false)?;

        let mut paragraphs = ParagraphVecShort::new();

        for para in IterBuf::new().try_iterate(items)? {
            let [key, value]: [Obj; 2] = util::iter_into_array(para)?;
            let key: StrBuffer = key.try_into()?;
            let value: StrBuffer = value.try_into()?;
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

        let obj = LayoutObj::new(
            Frame::left_aligned(
                title,
                SimplePage::new(paragraphs.into_paragraphs(), axis, theme::BG)
                    .with_swipe_right_to_go_back(),
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
        let chunkify: bool = kwargs.get_or(Qstr::MP_QSTR_chunkify, false)?;
        let text_mono: bool = kwargs.get_or(Qstr::MP_QSTR_text_mono, true)?;

        ConfirmBlobParams::new(title, value, description, verb, verb_cancel, hold)
            .with_subtitle(subtitle)
            .with_info_button(info_button)
            .with_chunkify(chunkify)
            .with_text_mono(text_mono)
            .into_layout()
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_confirm_total(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;
        let info_button: bool = kwargs.get_or(Qstr::MP_QSTR_info_button, false)?;
        let cancel_arrow: bool = kwargs.get_or(Qstr::MP_QSTR_cancel_arrow, false)?;

        let mut paragraphs = ParagraphVecShort::new();

        for pair in IterBuf::new().try_iterate(items)? {
            let [label, value]: [StrBuffer; 2] = util::iter_into_array(pair)?;
            paragraphs.add(Paragraph::new(&theme::TEXT_NORMAL, label).no_break());
            paragraphs.add(Paragraph::new(&theme::TEXT_MONO, value));
        }
        let mut page: ButtonPage<_, StrBuffer> =
            ButtonPage::new(paragraphs.into_paragraphs(), theme::BG).with_hold()?;
        if cancel_arrow {
            page = page.with_cancel_arrow()
        }
        if info_button {
            page = page.with_swipe_left();
        }
        let mut frame = Frame::left_aligned(title, page);
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
            TR::modify_amount__decrease_amount.try_into()?
        } else {
            TR::modify_amount__increase_amount.try_into()?
        };

        let paragraphs = Paragraphs::new([
            Paragraph::new(&theme::TEXT_NORMAL, description),
            Paragraph::new(&theme::TEXT_MONO, amount_change),
            Paragraph::new(
                &theme::TEXT_NORMAL,
                TR::modify_amount__new_amount.try_into()?,
            ),
            Paragraph::new(&theme::TEXT_MONO, amount_new),
        ]);

        let tr_title: StrBuffer = TR::modify_amount__title.try_into()?;
        let obj = LayoutObj::new(Frame::left_aligned(
            tr_title,
            ButtonPage::<_, StrBuffer>::new(paragraphs, theme::BG)
                .with_cancel_confirm(Some("^".into()), Some(TR::buttons__continue.try_into()?)),
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
            s if s < 0 => (
                TR::modify_fee__decrease_fee.try_into()?,
                user_fee_change,
                TR::modify_fee__new_transaction_fee.try_into()?,
            ),
            s if s > 0 => (
                TR::modify_fee__increase_fee.try_into()?,
                user_fee_change,
                TR::modify_fee__new_transaction_fee.try_into()?,
            ),
            _ => (
                TR::modify_fee__no_change.try_into()?,
                StrBuffer::empty(),
                TR::modify_fee__transaction_fee.try_into()?,
            ),
        };

        let paragraphs = Paragraphs::new([
            Paragraph::new(&theme::TEXT_NORMAL, description),
            Paragraph::new(&theme::TEXT_MONO, change),
            Paragraph::new(&theme::TEXT_NORMAL, total_label),
            Paragraph::new(&theme::TEXT_MONO, total_fee_new),
        ]);

        let obj = LayoutObj::new(
            Frame::left_aligned(
                title,
                ButtonPage::<_, StrBuffer>::new(paragraphs, theme::BG)
                    .with_hold()?
                    .with_swipe_left(),
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
    let value: StrBuffer = kwargs.get_or(Qstr::MP_QSTR_value, StrBuffer::empty())?;
    let description: StrBuffer = kwargs.get_or(Qstr::MP_QSTR_description, StrBuffer::empty())?;
    let button: StrBuffer =
        kwargs.get_or(Qstr::MP_QSTR_button, TR::buttons__continue.try_into()?)?;
    let allow_cancel: bool = kwargs.get_or(Qstr::MP_QSTR_allow_cancel, true)?;
    let time_ms: u32 = kwargs.get_or(Qstr::MP_QSTR_time_ms, 0)?;

    let no_buttons = button.as_ref().is_empty();
    let obj = if no_buttons && time_ms == 0 {
        // No buttons and no timer, used when we only want to draw the dialog once and
        // then throw away the layout object.
        LayoutObj::new(
            IconDialog::new(icon, title, Empty)
                .with_value(value)
                .with_description(description),
        )?
        .into()
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
            .with_value(value)
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
            .with_value(value)
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
            Button::<StrBuffer>::with_text(TR::buttons__confirm.try_into()?)
                .styled(theme::button_confirm()),
            true,
        );

        let fido_page = FidoConfirm::new(app_name, get_page, page_count, icon, controls);

        let obj = LayoutObj::new(Frame::centered(title, fido_page))?;
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

extern "C" fn new_show_mismatch(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: StrBuffer = TR::addr_mismatch__contact_support_at.try_into()?;
        let url: StrBuffer = TR::addr_mismatch__support_url.try_into()?;
        let button: StrBuffer = TR::buttons__quit.try_into()?;

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
            .with_paragraph(
                Paragraph::new(&theme::TEXT_NORMAL, description)
                    .centered()
                    .with_bottom_padding(
                        theme::TEXT_NORMAL.text_font.text_height()
                            - theme::TEXT_DEMIBOLD.text_font.text_height(),
                    ),
            )
            .with_text(&theme::TEXT_DEMIBOLD, url),
        )?;

        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_simple(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: Option<StrBuffer> = kwargs.get(Qstr::MP_QSTR_title)?.try_into_option()?;
        let description: StrBuffer =
            kwargs.get_or(Qstr::MP_QSTR_description, StrBuffer::empty())?;
        let button: StrBuffer = kwargs.get_or(Qstr::MP_QSTR_button, StrBuffer::empty())?;

        let obj = if let Some(t) = title {
            LayoutObj::new(Frame::left_aligned(
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
            let [font, text]: [Obj; 2] = util::iter_into_array(para)?;
            let style: &TextStyle = theme::textstyle_number(font.try_into()?);
            let text: StrBuffer = text.try_into()?;
            paragraphs.add(Paragraph::new(style, text));
            if paragraphs.is_full() {
                break;
            }
        }

        let buttons = Button::cancel_info_confirm(button, info_button);

        let obj = LayoutObj::new(Frame::left_aligned(
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
            let [font, text]: [Obj; 2] = util::iter_into_array(para)?;
            let style: &TextStyle = theme::textstyle_number(font.try_into()?);
            let text: StrBuffer = text.try_into()?;
            paragraphs.add(Paragraph::new(style, text));
        }

        let obj = LayoutObj::new(Frame::left_aligned(
            title,
            ButtonPage::new(paragraphs.into_paragraphs(), theme::BG)
                .with_cancel_confirm(None, Some(button))
                .with_confirm_style(theme::button_default())
                .with_back_button(),
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
            Paragraph::new(&theme::TEXT_NORMAL, TR::coinjoin__max_rounds.try_into()?),
            Paragraph::new(&theme::TEXT_MONO, max_rounds),
            Paragraph::new(
                &theme::TEXT_NORMAL,
                TR::coinjoin__max_mining_fee.try_into()?,
            ),
            Paragraph::new(&theme::TEXT_MONO, max_feerate),
        ]);

        let tr_title: StrBuffer = TR::coinjoin__title.try_into()?;
        let obj = LayoutObj::new(Frame::left_aligned(
            tr_title,
            ButtonPage::<_, StrBuffer>::new(paragraphs, theme::BG).with_hold()?,
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
            Some(TR::pin__wrong_pin.try_into()?)
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
        let prefill_word: StrBuffer = kwargs.get(Qstr::MP_QSTR_prefill_word)?.try_into()?;
        let can_go_back: bool = kwargs.get(Qstr::MP_QSTR_can_go_back)?.try_into()?;
        let obj = LayoutObj::new(MnemonicKeyboard::new(
            Bip39Input::prefilled_word(prefill_word.as_ref()),
            prompt,
            can_go_back,
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_request_slip39(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let prompt: StrBuffer = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let prefill_word: StrBuffer = kwargs.get(Qstr::MP_QSTR_prefill_word)?.try_into()?;
        let can_go_back: bool = kwargs.get(Qstr::MP_QSTR_can_go_back)?.try_into()?;
        let obj = LayoutObj::new(MnemonicKeyboard::new(
            Slip39Input::prefilled_word(prefill_word.as_ref()),
            prompt,
            can_go_back,
        ))?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_select_word(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: StrBuffer = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: StrBuffer = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let words_iterable: Obj = kwargs.get(Qstr::MP_QSTR_words)?;
        let words: [StrBuffer; 3] = util::iter_into_array(words_iterable)?;

        let content = VerticalMenu::select_word(words);
        let frame_with_menu = Frame::left_aligned(title, content).with_subtitle(description);
        let obj = LayoutObj::new(frame_with_menu)?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_show_tx_context_menu(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], _kwargs: &Map| {
        // TODO: this is just POC
        let title: StrBuffer = StrBuffer::from("");

        let options: [(StrBuffer, Icon); 3] = [
            (StrBuffer::from("Address QR code"), theme::ICON_QR_CODE),
            (StrBuffer::from("Fee info"), theme::ICON_CHEVRON_RIGHT),
            (StrBuffer::from("Cancel transaction"), theme::ICON_CANCEL),
        ];
        let content = VerticalMenu::context_menu(options);
        let frame_with_menu = Frame::left_aligned(title, content).with_cancel_button();
        let obj = LayoutObj::new(frame_with_menu)?;
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
            title,
            ButtonPage::<_, StrBuffer>::new(paragraphs.into_paragraphs(), theme::BG)
                .with_hold()?
                .without_cancel(),
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
            title,
            NumberInputDialog::new(min_count, max_count, count, callback)?,
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
            Paragraph::new(&theme::TEXT_DEMIBOLD, title),
            Paragraph::new(&theme::TEXT_NORMAL, description),
        ])
        .with_spacing(theme::RECOVERY_SPACING);

        let notification: StrBuffer = if dry_run {
            TR::recovery__title_dry_run.try_into()?
        } else {
            TR::recovery__title.try_into()?
        };

        let obj = if info_button {
            LayoutObj::new(Frame::left_aligned(
                notification,
                Dialog::new(
                    paragraphs,
                    Button::<StrBuffer>::cancel_info_confirm(
                        TR::buttons__continue.try_into()?,
                        TR::buttons__more_info.try_into()?,
                    ),
                ),
            ))?
        } else {
            LayoutObj::new(Frame::left_aligned(
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
        let title: StrBuffer = if dry_run {
            TR::recovery__title_dry_run.try_into()?
        } else {
            TR::recovery__title.try_into()?
        };

        let paragraphs = Paragraphs::new(Paragraph::<StrBuffer>::new(
            &theme::TEXT_DEMIBOLD,
            TR::recovery__select_num_of_words.try_into()?,
        ));

        let obj = LayoutObj::new(Frame::left_aligned(
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
        let lines: [StrBuffer; 4] = util::iter_into_array(lines_iterable)?;

        let obj = LayoutObj::new(IconDialog::new_shares(
            lines,
            theme::button_bar(
                Button::<StrBuffer>::with_text(TR::buttons__continue.try_into()?).map(|msg| {
                    (matches!(msg, ButtonMsg::Clicked)).then(|| CancelConfirmMsg::Confirmed)
                }),
            ),
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
            let [title, description]: [StrBuffer; 2] = util::iter_into_array(page)?;
            paragraphs
                .add(Paragraph::new(&theme::TEXT_DEMIBOLD, title))
                .add(Paragraph::new(&theme::TEXT_NORMAL, description).break_after());
        }

        let tr_title: StrBuffer = TR::recovery__title_remaining_shares.try_into()?;
        let obj = LayoutObj::new(Frame::left_aligned(
            tr_title,
            ButtonPage::<_, StrBuffer>::new(paragraphs.into_paragraphs(), theme::BG)
                .with_cancel_confirm(None, Some(TR::buttons__continue.try_into()?))
                .with_confirm_style(theme::button_default())
                .without_cancel(),
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
        let progress = CoinJoinProgress::<_, Never>::new(title, indeterminate)?;
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
        let buffer = unsafe { get_buffer(data) }?;

        Ok(check_homescreen_format(buffer).into())
    };

    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
extern "C" fn new_confirm_firmware_update(
    n_args: usize,
    args: *const Obj,
    kwargs: *mut Map,
) -> Obj {
    use super::component::bl_confirm::{Confirm, ConfirmTitle};
    let block = move |_args: &[Obj], kwargs: &Map| {
        let description: StrBuffer = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let fingerprint: StrBuffer = kwargs.get(Qstr::MP_QSTR_fingerprint)?.try_into()?;

        let title_str = TR::firmware_update__title.try_into()?;
        let title = Label::left_aligned(title_str, theme::TEXT_BOLD).vertically_centered();
        let msg = Label::left_aligned(description, theme::TEXT_NORMAL);

        let left =
            Button::with_text(TR::buttons__cancel.try_into()?).styled(theme::button_default());
        let right =
            Button::with_text(TR::buttons__install.try_into()?).styled(theme::button_confirm());

        let obj = LayoutObj::new(
            Confirm::new(theme::BG, left, right, ConfirmTitle::Text(title), msg).with_info(
                TR::firmware_update__title_fingerprint.try_into()?,
                fingerprint,
                theme::button_moreinfo(),
            ),
        )?;
        Ok(obj.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
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
    /// from trezor import utils
    ///
    /// T = TypeVar("T")
    ///
    /// class LayoutObj(Generic[T]):
    ///     """Representation of a Rust-based layout object.
    ///     see `trezor::ui::layout::obj::LayoutObj`.
    ///     """
    ///
    ///     def attach_timer_fn(self, fn: Callable[[int, int], None]) -> None:
    ///         """Attach a timer setter function.
    ///
    ///         The layout object can call the timer setter with two arguments,
    ///         `token` and `deadline`. When `deadline` is reached, the layout object
    ///         expects a callback to `self.timer(token)`.
    ///         """
    ///
    ///     if utils.USE_TOUCH:
    ///         def touch_event(self, event: int, x: int, y: int) -> T | None:
    ///             """Receive a touch event `event` at coordinates `x`, `y`."""
    ///
    ///     if utils.USE_BUTTON:
    ///         def button_event(self, event: int, button: int) -> T | None:
    ///             """Receive a button event `event` for button `button`."""
    ///
    ///     def progress_event(self, value: int, description: str) -> T | None:
    ///         """Receive a progress event."""
    ///
    ///     def usb_event(self, connected: bool) -> T | None:
    ///         """Receive a USB connect/disconnect event."""
    ///
    ///     def timer(self, token: int) -> T | None:
    ///         """Callback for the timer set by `attach_timer_fn`.
    ///
    ///         This function should be called by the executor after the corresponding
    ///         deadline is reached.
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
    /// class UiResult:
    ///    """Result of a UI operation."""
    ///    pass
    ///
    /// mock:global
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
    ///     verb: str | None = None,
    ///     verb_cancel: str | None = None,
    ///     hold: bool = False,
    ///     hold_danger: bool = False,
    ///     reverse: bool = False,
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
    ///     extra: str | None,
    ///     verb: str | None = None,
    ///     verb_cancel: str | None = None,
    ///     hold: bool = False,
    ///     chunkify: bool = False,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm byte sequence data."""
    Qstr::MP_QSTR_confirm_blob => obj_fn_kw!(0, new_confirm_blob).as_obj(),

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

    /// def confirm_reset_device(
    ///     *,
    ///     title: str,
    ///     button: str,
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm TOS before device setup."""
    Qstr::MP_QSTR_confirm_reset_device => obj_fn_kw!(0, new_confirm_reset_device).as_obj(),

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
    /// ) -> LayoutObj[UiResult]:
    ///     """Warning modal. No buttons shown when `button` is empty string."""
    Qstr::MP_QSTR_show_warning => obj_fn_kw!(0, new_show_warning).as_obj(),

    /// def show_success(
    ///     *,
    ///     title: str,
    ///     button: str = "CONTINUE",
    ///     description: str = "",
    ///     allow_cancel: bool = False,
    ///     time_ms: int = 0,
    /// ) -> LayoutObj[UiResult]:
    ///     """Success modal. No buttons shown when `button` is empty string."""
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
    ///     """Confirm given items but with third button. Always single page
    ///     without scrolling."""
    Qstr::MP_QSTR_confirm_with_info => obj_fn_kw!(0, new_confirm_with_info).as_obj(),

    /// def confirm_more(
    ///     *,
    ///     title: str,
    ///     button: str,
    ///     items: Iterable[tuple[int, str]],
    /// ) -> LayoutObj[UiResult]:
    ///     """Confirm long content with the possibility to go back from any page.
    ///     Meant to be used with confirm_with_info."""
    Qstr::MP_QSTR_confirm_more => obj_fn_kw!(0, new_confirm_more).as_obj(),

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

    /// def request_passphrase(
    ///     *,
    ///     prompt: str,
    ///     max_len: int,
    /// ) -> LayoutObj[str | UiResult]:
    ///     """Passphrase input keyboard."""
    Qstr::MP_QSTR_request_passphrase => obj_fn_kw!(0, new_request_passphrase).as_obj(),

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

    /// def show_tx_context_menu() -> LayoutObj[int]:
    ///    """Show transaction context menu with the options for 1) Address QR code, 2) Fee
    ///    information, 3) Cancel transaction"""
    Qstr::MP_QSTR_show_tx_context_menu => obj_fn_kw!(0, new_show_tx_context_menu).as_obj(),

    /// def show_share_words(
    ///     *,
    ///     title: str,
    ///     pages: Iterable[str],
    /// ) -> LayoutObj[UiResult]:
    ///     """Show mnemonic for backup. Expects the words pre-divided into individual pages."""
    Qstr::MP_QSTR_show_share_words => obj_fn_kw!(0, new_show_share_words).as_obj(),

    /// def request_number(
    ///     *,
    ///     title: str,
    ///     count: int,
    ///     min_count: int,
    ///     max_count: int,
    ///     description: Callable[[int], str] | None = None,
    /// ) -> LayoutObj[tuple[UiResult, int]]:
    ///     """Number input with + and - buttons, description, and info button."""
    Qstr::MP_QSTR_request_number => obj_fn_kw!(0, new_request_number).as_obj(),

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

    /// def confirm_recovery(
    ///     *,
    ///     title: str,
    ///     description: str,
    ///     button: str,
    ///     dry_run: bool,
    ///     info_button: bool = False,
    /// ) -> LayoutObj[UiResult]:
    ///     """Device recovery homescreen."""
    Qstr::MP_QSTR_confirm_recovery => obj_fn_kw!(0, new_confirm_recovery).as_obj(),

    /// def select_word_count(
    ///     *,
    ///     dry_run: bool,
    /// ) -> LayoutObj[int | str]:  # TT returns int
    ///     """Select mnemonic word count from (12, 18, 20, 24, 33)."""
    Qstr::MP_QSTR_select_word_count => obj_fn_kw!(0, new_select_word_count).as_obj(),

    /// def show_group_share_success(
    ///     *,
    ///     lines: Iterable[str]
    /// ) -> LayoutObj[UiResult]:
    ///     """Shown after successfully finishing a group."""
    Qstr::MP_QSTR_show_group_share_success => obj_fn_kw!(0, new_show_group_share_success).as_obj(),

    /// def show_remaining_shares(
    ///     *,
    ///     pages: Iterable[tuple[str, str]],
    /// ) -> LayoutObj[UiResult]:
    ///     """Shows SLIP39 state after info button is pressed on `confirm_recovery`."""
    Qstr::MP_QSTR_show_remaining_shares => obj_fn_kw!(0, new_show_remaining_shares).as_obj(),

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
    ///     """Ask whether to update firmware, optionally show fingerprint. Shared with bootloader."""
    Qstr::MP_QSTR_confirm_firmware_update => obj_fn_kw!(0, new_confirm_firmware_update).as_obj(),

    /// def show_wait_text(message: str, /) -> LayoutObj[None]:
    ///     """Show single-line text in the middle of the screen."""
    Qstr::MP_QSTR_show_wait_text => obj_fn_1!(new_show_wait_text).as_obj(),
};

#[cfg(test)]
mod tests {
    use serde_json;

    use crate::{
        trace::tests::trace,
        ui::{component::text::op::OpTextLayout, geometry::Rect, model_mercury::constant},
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
