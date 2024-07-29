use crate::{
    error,
    micropython::{iter::IterBuf, map::Map, obj::Obj, qstr::Qstr, util},
    strutil::TString,
    translations::TR,
    ui::{
        button_request::ButtonRequest,
        component::{
            swipe_detect::SwipeSettings,
            text::paragraphs::{Paragraph, ParagraphSource, Paragraphs},
            ButtonRequestExt, ComponentExt, Qr, SwipeDirection,
        },
        flow::{
            base::{DecisionBuilder as _, StateChange},
            FlowMsg, FlowState, SwipeFlow, SwipePage,
        },
        layout::{obj::LayoutObj, util::ConfirmBlob},
    },
};

use super::super::{
    component::{
        AddressDetails, Frame, FrameMsg, PromptMsg, PromptScreen, StatusScreen, SwipeContent,
        VerticalMenu, VerticalMenuChoiceMsg,
    },
    theme,
};

const QR_BORDER: i16 = 4;

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum GetAddress {
    Address,
    Tap,
    Confirmed,
    Menu,
    QrCode,
    AccountInfo,
    Cancel,
    CancelTap,
}

impl FlowState for GetAddress {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: SwipeDirection) -> StateChange {
        match (self, direction) {
            (Self::Address, SwipeDirection::Left) => Self::Menu.swipe(direction),
            (Self::Address, SwipeDirection::Up) => Self::Tap.swipe(direction),
            (Self::Tap, SwipeDirection::Down) => Self::Address.swipe(direction),
            (Self::Tap, SwipeDirection::Left) => Self::Menu.swipe(direction),
            (Self::Menu, SwipeDirection::Right) => Self::Address.swipe(direction),
            (Self::QrCode, SwipeDirection::Right) => Self::Menu.swipe(direction),
            (Self::AccountInfo, SwipeDirection::Right) => Self::Menu.swipe_right(),
            (Self::Cancel, SwipeDirection::Up) => Self::CancelTap.swipe(direction),
            (Self::Cancel, SwipeDirection::Right) => Self::Menu.swipe(direction),
            (Self::CancelTap, SwipeDirection::Down) => Self::Cancel.swipe(direction),
            (Self::CancelTap, SwipeDirection::Right) => Self::Menu.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> StateChange {
        match (self, msg) {
            (Self::Address, FlowMsg::Info) => Self::Menu.transit(),
            (Self::Tap, FlowMsg::Confirmed) => Self::Confirmed.swipe_up(),
            (Self::Tap, FlowMsg::Info) => Self::Menu.swipe_left(),
            (Self::Confirmed, _) => self.return_msg(FlowMsg::Confirmed),
            (Self::Menu, FlowMsg::Choice(0)) => Self::QrCode.swipe_left(),
            (Self::Menu, FlowMsg::Choice(1)) => Self::AccountInfo.swipe_left(),
            (Self::Menu, FlowMsg::Choice(2)) => Self::Cancel.swipe_left(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Address.swipe_right(),
            (Self::QrCode, FlowMsg::Cancelled) => Self::Menu.transit(),
            (Self::AccountInfo, FlowMsg::Cancelled) => Self::Menu.transit(),
            (Self::Cancel, FlowMsg::Cancelled) => Self::Menu.transit(),
            (Self::CancelTap, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Cancelled),
            (Self::CancelTap, FlowMsg::Cancelled) => Self::Menu.transit(),
            _ => self.do_nothing(),
        }
    }
}

#[allow(clippy::not_unsafe_ptr_arg_deref)]
pub extern "C" fn new_get_address(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, GetAddress::new_obj) }
}

impl GetAddress {
    fn new_obj(_args: &[Obj], kwargs: &Map) -> Result<Obj, error::Error> {
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

        // Address
        let data_style = if chunkify {
            let address: TString = address.try_into()?;
            theme::get_chunkified_text_style(address.len())
        } else {
            &theme::TEXT_MONO
        };
        let paragraphs = ConfirmBlob {
            description: description.unwrap_or("".into()),
            extra: extra.unwrap_or("".into()),
            data: address.try_into()?,
            description_font: &theme::TEXT_NORMAL,
            extra_font: &theme::TEXT_DEMIBOLD,
            data_font: data_style,
        }
        .into_paragraphs();
        let content_address =
            Frame::left_aligned(title, SwipeContent::new(SwipePage::vertical(paragraphs)))
                .with_menu_button()
                .with_footer(TR::instructions__swipe_up.into(), None)
                .with_swipe(SwipeDirection::Up, SwipeSettings::default())
                .with_swipe(SwipeDirection::Left, SwipeSettings::default())
                .with_vertical_pages()
                .map(|msg| matches!(msg, FrameMsg::Button(_)).then_some(FlowMsg::Info))
                .one_button_request(ButtonRequest::from_num(br_code, br_name))
                // Count tap-to-confirm screen towards page count
                .with_pages(|address_pages| address_pages + 1);

        // Tap
        let content_tap =
            Frame::left_aligned(title, SwipeContent::new(PromptScreen::new_tap_to_confirm()))
                .with_footer(TR::instructions__tap_to_confirm.into(), None)
                .with_swipe(SwipeDirection::Down, SwipeSettings::default())
                .with_swipe(SwipeDirection::Left, SwipeSettings::default())
                .map(|msg| match msg {
                    FrameMsg::Content(PromptMsg::Confirmed) => Some(FlowMsg::Confirmed),
                    FrameMsg::Button(_) => Some(FlowMsg::Info),
                    _ => None,
                });

        let content_confirmed = Frame::left_aligned(
            TR::words__title_success.into(),
            StatusScreen::new_success_timeout(TR::address__confirmed.into()),
        )
        .with_footer(TR::instructions__continue_in_app.into(), None)
        .with_result_icon(theme::ICON_BULLET_CHECKMARK, theme::GREEN_LIGHT)
        .map(|_| Some(FlowMsg::Confirmed));

        // Menu
        let content_menu = Frame::left_aligned(
            "".into(),
            VerticalMenu::empty()
                .item(theme::ICON_QR_CODE, TR::address__qr_code.into())
                .item(
                    theme::ICON_CHEVRON_RIGHT,
                    TR::address_details__account_info.into(),
                )
                .danger(theme::ICON_CANCEL, TR::address__cancel_receive.into()),
        )
        .with_cancel_button()
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| match msg {
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
            FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
        });

        // QrCode
        let content_qr = Frame::left_aligned(
            title,
            address_qr
                .map(|s| Qr::new(s, case_sensitive))?
                .with_border(QR_BORDER),
        )
        .with_cancel_button()
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| matches!(msg, FrameMsg::Button(_)).then_some(FlowMsg::Cancelled));

        // AccountInfo
        let mut ad = AddressDetails::new(TR::address_details__account_info.into(), account, path)?;
        for i in IterBuf::new().try_iterate(xpubs)? {
            let [xtitle, text]: [TString; 2] = util::iter_into_array(i)?;
            ad.add_xpub(xtitle, text)?;
        }
        let content_account = ad.map(|_| Some(FlowMsg::Cancelled));

        // Cancel
        let content_cancel_info = Frame::left_aligned(
            TR::address__cancel_receive.into(),
            SwipeContent::new(Paragraphs::new(Paragraph::new(
                &theme::TEXT_MAIN_GREY_LIGHT,
                TR::address__cancel_contact_support,
            ))),
        )
        .with_cancel_button()
        .with_footer(TR::instructions__swipe_up.into(), None)
        .with_swipe(SwipeDirection::Up, SwipeSettings::default())
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| matches!(msg, FrameMsg::Button(_)).then_some(FlowMsg::Cancelled));

        // CancelTap
        let content_cancel_tap = Frame::left_aligned(
            TR::address__cancel_receive.into(),
            PromptScreen::new_tap_to_cancel(),
        )
        .with_cancel_button()
        .with_footer(TR::instructions__tap_to_confirm.into(), None)
        .with_swipe(SwipeDirection::Down, SwipeSettings::default())
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| match msg {
            FrameMsg::Content(PromptMsg::Confirmed) => Some(FlowMsg::Confirmed),
            FrameMsg::Button(FlowMsg::Cancelled) => Some(FlowMsg::Cancelled),
            _ => None,
        });

        let res = SwipeFlow::new(&GetAddress::Address)?
            .with_page(&GetAddress::Address, content_address)?
            .with_page(&GetAddress::Tap, content_tap)?
            .with_page(&GetAddress::Confirmed, content_confirmed)?
            .with_page(&GetAddress::Menu, content_menu)?
            .with_page(&GetAddress::QrCode, content_qr)?
            .with_page(&GetAddress::AccountInfo, content_account)?
            .with_page(&GetAddress::Cancel, content_cancel_info)?
            .with_page(&GetAddress::CancelTap, content_cancel_tap)?;
        Ok(LayoutObj::new(res)?.into())
    }
}
