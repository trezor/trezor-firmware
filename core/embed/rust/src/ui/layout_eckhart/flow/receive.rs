use crate::{
    error,
    micropython::{obj::Obj, util},
    strutil::TString,
    translations::TR,
    ui::{
        button_request::ButtonRequest,
        component::{
            text::paragraphs::{
                Paragraph, ParagraphSource, ParagraphVecLong, ParagraphVecShort, VecExt,
            },
            ButtonRequestExt, ComponentExt, Qr,
        },
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::{Direction, LinearPlacement},
    },
};
use heapless::Vec;

use super::super::{
    component::Button,
    firmware::{
        ActionBar, Header, HeaderMsg, Hint, QrScreen, ShortMenuVec, TextScreen, TextScreenMsg,
        VerticalMenu, VerticalMenuScreen, VerticalMenuScreenMsg,
    },
    theme,
};

const ITEM_PADDING: i16 = 16;
const GROUP_PADDING: i16 = 20;
const MAX_XPUBS: usize = 3;

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum Receive {
    Content,
    Menu,
    QrCode,
    AccountInfo,
    Cancel,
}

impl FlowController for Receive {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, _direction: Direction) -> Decision {
        self.do_nothing()
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Content, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Content, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            (Self::Menu, FlowMsg::Choice(0)) => Self::QrCode.swipe_left(),
            (Self::Menu, FlowMsg::Choice(1)) => Self::AccountInfo.swipe_left(),
            (Self::Menu, FlowMsg::Choice(2)) => Self::Cancel.swipe_left(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Content.swipe_right(),
            (Self::QrCode, FlowMsg::Cancelled) => Self::Menu.goto(),
            (Self::AccountInfo, FlowMsg::Cancelled) => Self::Menu.goto(),
            (Self::Cancel, FlowMsg::Cancelled) => Self::Content.goto(),
            (Self::Cancel, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Cancelled),
            _ => self.do_nothing(),
        }
    }
}

#[allow(clippy::too_many_arguments)]
pub fn new_receive(
    title: TString<'static>,
    subtitle: Option<TString<'static>>,
    description: Option<TString<'static>>,
    extra: Option<TString<'static>>,
    content: Obj, // TODO: get rid of Obj
    address: bool,
    chunkify: bool,
    qr: TString<'static>,
    case_sensitive: bool,
    account: Option<TString<'static>>,
    path: Option<TString<'static>>,
    xpubs: Obj, // TODO: get rid of Obj
    br_code: u16,
    br_name: TString<'static>,
) -> Result<SwipeFlow, error::Error> {
    let text_style = if chunkify {
        let content: TString = content.try_into()?;
        theme::get_chunkified_text_style(content.len())
    } else {
        &theme::TEXT_MONO_ADDRESS
    };

    let mut paragraphs = ParagraphVecShort::new();
    if let Some(description) = description {
        paragraphs.add(
            Paragraph::new(&theme::TEXT_SMALL_LIGHT, description).with_bottom_padding(ITEM_PADDING),
        );
    }
    paragraphs.add(Paragraph::new(
        text_style,
        content.try_into().unwrap_or(TString::empty()),
    ));

    let button = if extra.is_some() {
        Button::with_text(TR::buttons__confirm.into()).styled(theme::button_cancel_gradient())
    } else {
        Button::with_text(TR::buttons__confirm.into()).styled(theme::button_confirm())
    };

    let mut address_screen = TextScreen::new(
        paragraphs
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical()),
    )
    .with_header(Header::new(title).with_menu_button())
    .with_subtitle(subtitle.unwrap_or(TString::empty()))
    .with_action_bar(ActionBar::new_single(button));
    if let Some(extra) = extra {
        address_screen = address_screen.with_hint(Hint::new_warning_caution(extra));
    }
    let content_address = address_screen
        .map(|msg| match msg {
            TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
            TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
            TextScreenMsg::Menu => Some(FlowMsg::Info),
        })
        .one_button_request(ButtonRequest::from_num(br_code, br_name));

    // Menu
    let content_menu = VerticalMenuScreen::new(
        VerticalMenu::<ShortMenuVec>::empty()
            .with_item(Button::new_menu_item(
                TR::address__qr_code.into(),
                theme::menu_item_title(),
            ))
            .with_item(Button::new_menu_item(
                TR::address_details__account_info.into(),
                theme::menu_item_title(),
            ))
            .with_item(Button::new_menu_item(
                TR::buttons__cancel.into(),
                theme::menu_item_title_orange(),
            )),
    )
    .with_header(
        Header::new(title)
            .with_right_button(Button::with_icon(theme::ICON_CROSS), HeaderMsg::Cancelled),
    )
    .map(|msg| match msg {
        VerticalMenuScreenMsg::Selected(i) => Some(FlowMsg::Choice(i)),
        VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
        _ => None,
    });

    // QrCode
    let title_qr = match address {
        true => TR::address_details__title_receive_address,
        false => TR::address__xpub,
    };
    let content_qr = QrScreen::new(qr.map(|s| Qr::new(s, case_sensitive))?)
        .with_header(
            Header::new(title_qr.into())
                .with_right_button(Button::with_icon(theme::ICON_CROSS), HeaderMsg::Cancelled),
        )
        .map(|_| Some(FlowMsg::Cancelled));

    // AccountInfo
    let mut para = ParagraphVecLong::new();
    if let Some(a) = account {
        para.add(Paragraph::new::<TString>(
            &theme::TEXT_SMALL_LIGHT,
            TR::words__account.into(),
        ));
        para.add(Paragraph::new(&theme::TEXT_MONO_EXTRA_LIGHT, a).with_top_padding(ITEM_PADDING));
    }

    if let Some(p) = path {
        para.add(
            Paragraph::new::<TString>(
                &theme::TEXT_SMALL_LIGHT,
                TR::address_details__derivation_path.into(),
            )
            .with_top_padding(GROUP_PADDING)
            .no_break(),
        );
        para.add(
            Paragraph::new(&theme::TEXT_MONO_EXTRA_LIGHT, p)
                .with_top_padding(ITEM_PADDING)
                .break_after(),
        );
    }

    let xpub_items: Vec<Obj, MAX_XPUBS> = util::iter_into_vec(xpubs).unwrap_or(Vec::new());
    for i in xpub_items.into_iter() {
        let [label, value]: [TString; 2] = util::iter_into_array(i)?;
        para.add(Paragraph::new(&theme::TEXT_SMALL_LIGHT, label).no_break());
        para.add(
            Paragraph::new(&theme::TEXT_MONO_LIGHT, value)
                .with_top_padding(ITEM_PADDING)
                .break_after(),
        );
    }

    let content_account = TextScreen::new(
        para.into_paragraphs()
            .with_placement(LinearPlacement::vertical()),
    )
    .with_header(
        Header::new(TR::address_details__account_info.into())
            .with_right_button(Button::with_icon(theme::ICON_CROSS), HeaderMsg::Cancelled),
    )
    .map(|_| Some(FlowMsg::Cancelled));

    // Cancel
    let cancel_info = match address {
        true => TR::address__cancel_receive,
        false => TR::words__cancel_question,
    };
    let mut screen_cancel_info = TextScreen::new(
        Paragraph::new(&theme::TEXT_REGULAR, cancel_info)
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical()),
    )
    .with_header(Header::new(title))
    .with_action_bar(ActionBar::new_double(
        Button::with_icon(theme::ICON_CHEVRON_LEFT),
        Button::with_text(TR::buttons__cancel.into()).styled(theme::button_cancel()),
    ));
    if address {
        screen_cancel_info = screen_cancel_info.with_hint(Hint::new_instruction(
            TR::address__cancel_contact_support,
            Some(theme::ICON_INFO),
        ))
    }

    let content_cancel_info = screen_cancel_info.map(|msg| match msg {
        TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
        TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
        _ => None,
    });

    let mut res = SwipeFlow::new(&Receive::Content)?;
    res.add_page(&Receive::Content, content_address)?
        .add_page(&Receive::Menu, content_menu)?
        .add_page(&Receive::QrCode, content_qr)?
        .add_page(&Receive::AccountInfo, content_account)?
        .add_page(&Receive::Cancel, content_cancel_info)?;
    Ok(res)
}
