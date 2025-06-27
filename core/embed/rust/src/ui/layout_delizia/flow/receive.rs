use crate::{
    error,
    micropython::{buffer::StrBuffer, obj::Obj, util},
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
        layout::util::{ConfirmValueParams, ContentType, MAX_XPUBS},
    },
};
use heapless::Vec;

use super::super::{
    component::{AddressDetails, Frame, PromptScreen, SwipeContent, VerticalMenu},
    theme,
};

const QR_BORDER: i16 = 4;

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum Receive {
    Content,
    Tap,
    Menu,
    QrCode,
    AccountInfo,
    Cancel,
    CancelTap,
}

impl FlowController for Receive {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Content, Direction::Up) => Self::Tap.swipe(direction),
            (Self::Tap, Direction::Down) => Self::Content.swipe(direction),
            (Self::Cancel, Direction::Up) => Self::CancelTap.swipe(direction),
            (Self::CancelTap, Direction::Down) => Self::Cancel.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Content, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Tap, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            (Self::Tap, FlowMsg::Info) => Self::Menu.swipe_left(),
            (Self::Menu, FlowMsg::Choice(0)) => Self::QrCode.swipe_left(),
            (Self::Menu, FlowMsg::Choice(1)) => Self::AccountInfo.swipe_left(),
            (Self::Menu, FlowMsg::Choice(2)) => Self::Cancel.swipe_left(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Content.swipe_right(),
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
pub fn new_receive(
    title: TString<'static>,
    description: Option<TString<'static>>,
    content: ContentType,
    chunkify: bool,
    qr: TString<'static>,
    case_sensitive: bool,
    account: Option<TString<'static>>,
    path: Option<TString<'static>>,
    xpubs: Obj, // TODO: get rid of Obj
    br_code: u16,
    br_name: TString<'static>,
) -> Result<SwipeFlow, error::Error> {
    let (content, cancel_title, cancel_content) = match content {
        ContentType::Address(address) => (
            address,
            TR::address__cancel_receive,
            TR::address__cancel_contact_support,
        ),
        ContentType::PublicKey(pubkey) => (pubkey, TR::buttons__cancel, TR::words__are_you_sure),
    };
    // Address
    let paragraphs = ConfirmValueParams {
        description: description.unwrap_or_else(|| "".into()),
        extra: "".into(),
        value: content.into(),
        font: if chunkify {
            theme::get_chunkified_text_style(content.len())
        } else {
            &theme::TEXT_MONO_DATA
        },
        description_font: &theme::TEXT_NORMAL,
        extra_font: &theme::TEXT_DEMIBOLD,
    }
    .into_paragraphs();
    let content_address =
        Frame::left_aligned(title, SwipeContent::new(SwipePage::vertical(paragraphs)))
            .with_menu_button()
            .with_swipeup_footer(None)
            .with_vertical_pages()
            .map_to_button_msg()
            .one_button_request(ButtonRequest::from_num(br_code, br_name))
            // Count tap-to-confirm screen towards page count
            .with_pages(|address_pages| address_pages + 1);

    // Tap
    let content_tap =
        Frame::left_aligned(title, SwipeContent::new(PromptScreen::new_tap_to_confirm()))
            .with_footer(TR::instructions__tap_to_confirm.into(), None)
            .with_swipe(Direction::Down, SwipeSettings::default())
            .map(super::util::map_to_confirm);

    // Menu
    let content_menu = Frame::left_aligned(
        "".into(),
        VerticalMenu::empty()
            .item(theme::ICON_QR_CODE, TR::address__qr_code.into())
            .item(
                theme::ICON_CHEVRON_RIGHT,
                TR::address_details__account_info.into(),
            )
            .danger(theme::ICON_CANCEL, cancel_title.into()),
    )
    .with_cancel_button()
    .map(super::util::map_to_choice);

    // QrCode
    let content_qr = Frame::left_aligned(
        title,
        qr.map(|s| Qr::new(s, case_sensitive))?
            .with_border(QR_BORDER),
    )
    .with_cancel_button()
    .map_to_button_msg();

    // AccountInfo
    let mut ad = AddressDetails::new(TR::address_details__account_info.into(), account, path)?;
    let xpub_items: Vec<Obj, MAX_XPUBS> = util::iter_into_vec(xpubs).unwrap_or(Vec::new());
    for i in xpub_items.into_iter() {
        let [xtitle, text]: [StrBuffer; 2] = util::iter_into_array(i)?;
        ad.add_xpub(xtitle, text)?;
    }
    let content_account = ad.map(|_| Some(FlowMsg::Cancelled));

    // Cancel
    let content_cancel_info = Frame::left_aligned(
        cancel_title.into(),
        SwipeContent::new(Paragraphs::new(Paragraph::new(
            &theme::TEXT_MAIN_GREY_LIGHT,
            cancel_content,
        ))),
    )
    .with_cancel_button()
    .with_swipeup_footer(None)
    .map_to_button_msg();

    // CancelTap
    let content_cancel_tap =
        Frame::left_aligned(cancel_title.into(), PromptScreen::new_tap_to_cancel())
            .with_cancel_button()
            .with_footer(TR::instructions__tap_to_confirm.into(), None)
            .with_swipe(Direction::Down, SwipeSettings::default())
            .map(super::util::map_to_confirm);

    let mut res = SwipeFlow::new(&Receive::Content)?;
    res.add_page(&Receive::Content, content_address)?
        .add_page(&Receive::Tap, content_tap)?
        .add_page(&Receive::Menu, content_menu)?
        .add_page(&Receive::QrCode, content_qr)?
        .add_page(&Receive::AccountInfo, content_account)?
        .add_page(&Receive::Cancel, content_cancel_info)?
        .add_page(&Receive::CancelTap, content_cancel_tap)?;
    Ok(res)
}
