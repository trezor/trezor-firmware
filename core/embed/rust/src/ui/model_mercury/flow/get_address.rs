use crate::{
    error,
    micropython::{iter::IterBuf, obj::Obj, util},
    strutil::TString,
    translations::TR,
    ui::{
        button_request::ButtonRequest,
        component::{
            swipe_detect::SwipeSettings,
            text::paragraphs::{Paragraph, ParagraphSource, Paragraphs},
            ButtonRequestExt, ComponentExt, Qr,
        },
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow, SwipePage,
        },
        geometry::Direction,
        layout::util::ConfirmBlob,
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

impl FlowController for GetAddress {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Address, Direction::Left) => Self::Menu.swipe(direction),
            (Self::Address, Direction::Up) => Self::Tap.swipe(direction),
            (Self::Tap, Direction::Down) => Self::Address.swipe(direction),
            (Self::Tap, Direction::Left) => Self::Menu.swipe(direction),
            (Self::Menu, Direction::Right) => Self::Address.swipe(direction),
            (Self::QrCode, Direction::Right) => Self::Menu.swipe(direction),
            (Self::AccountInfo, Direction::Right) => Self::Menu.swipe_right(),
            (Self::Cancel, Direction::Up) => Self::CancelTap.swipe(direction),
            (Self::Cancel, Direction::Right) => Self::Menu.swipe(direction),
            (Self::CancelTap, Direction::Down) => Self::Cancel.swipe(direction),
            (Self::CancelTap, Direction::Right) => Self::Menu.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Address, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Tap, FlowMsg::Confirmed) => Self::Confirmed.swipe_up(),
            (Self::Tap, FlowMsg::Info) => Self::Menu.swipe_left(),
            (Self::Confirmed, _) => self.return_msg(FlowMsg::Confirmed),
            (Self::Menu, FlowMsg::Choice(0)) => Self::QrCode.swipe_left(),
            (Self::Menu, FlowMsg::Choice(1)) => Self::AccountInfo.swipe_left(),
            (Self::Menu, FlowMsg::Choice(2)) => Self::Cancel.swipe_left(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Address.swipe_right(),
            (Self::QrCode, FlowMsg::Cancelled) => Self::Menu.goto(),
            (Self::AccountInfo, FlowMsg::Cancelled) => Self::Menu.goto(),
            (Self::Cancel, FlowMsg::Cancelled) => Self::Menu.goto(),
            (Self::CancelTap, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Cancelled),
            (Self::CancelTap, FlowMsg::Cancelled) => Self::Menu.goto(),
            _ => self.do_nothing(),
        }
    }
}

#[allow(clippy::too_many_arguments)]
pub fn new_get_address(
    title: TString<'static>,
    description: Option<TString<'static>>,
    extra: Option<TString<'static>>,
    address: Obj, // TODO: get rid of Obj
    chunkify: bool,
    address_qr: TString<'static>,
    case_sensitive: bool,
    account: Option<TString<'static>>,
    path: Option<TString<'static>>,
    xpubs: Obj, // TODO: get rid of Obj
    title_success: TString<'static>,
    br_code: u16,
    br_name: TString<'static>,
) -> Result<SwipeFlow, error::Error> {
    // Address
    let data_style = if chunkify {
        let address: TString = address.try_into()?;
        theme::get_chunkified_text_style(address.len())
    } else {
        &theme::TEXT_MONO
    };
    let paragraphs = ConfirmBlob {
        description: description.unwrap_or_else(|| "".into()),
        extra: extra.unwrap_or_else(|| "".into()),
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
            .with_swipe(Direction::Up, SwipeSettings::default())
            .with_swipe(Direction::Left, SwipeSettings::default())
            .with_vertical_pages()
            .map(|msg| matches!(msg, FrameMsg::Button(_)).then_some(FlowMsg::Info))
            .one_button_request(ButtonRequest::from_num(br_code, br_name))
            // Count tap-to-confirm screen towards page count
            .with_pages(|address_pages| address_pages + 1);

    // Tap
    let content_tap =
        Frame::left_aligned(title, SwipeContent::new(PromptScreen::new_tap_to_confirm()))
            .with_footer(TR::instructions__tap_to_confirm.into(), None)
            .with_swipe(Direction::Down, SwipeSettings::default())
            .with_swipe(Direction::Left, SwipeSettings::default())
            .map(|msg| match msg {
                FrameMsg::Content(PromptMsg::Confirmed) => Some(FlowMsg::Confirmed),
                FrameMsg::Button(_) => Some(FlowMsg::Info),
                _ => None,
            });

    let content_confirmed = Frame::left_aligned(
        TR::words__title_success.into(),
        StatusScreen::new_success_timeout(title_success),
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
    .with_swipe(Direction::Right, SwipeSettings::immediate())
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
    .with_swipe(Direction::Right, SwipeSettings::immediate())
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
    .with_swipe(Direction::Up, SwipeSettings::default())
    .with_swipe(Direction::Right, SwipeSettings::immediate())
    .map(|msg| matches!(msg, FrameMsg::Button(_)).then_some(FlowMsg::Cancelled));

    // CancelTap
    let content_cancel_tap = Frame::left_aligned(
        TR::address__cancel_receive.into(),
        PromptScreen::new_tap_to_cancel(),
    )
    .with_cancel_button()
    .with_footer(TR::instructions__tap_to_confirm.into(), None)
    .with_swipe(Direction::Down, SwipeSettings::default())
    .with_swipe(Direction::Right, SwipeSettings::immediate())
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
    Ok(res)
}
