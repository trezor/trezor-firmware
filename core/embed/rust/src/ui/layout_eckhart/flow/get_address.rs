use crate::{
    error,
    micropython::obj::Obj,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            text::paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort, VecExt},
            ComponentExt, Qr,
        },
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::{Alignment, Direction, LinearPlacement, Offset},
        layout::util::ConfirmValueParams,
    },
};

use super::super::{
    component::Button,
    firmware::{
        ActionBar, Header, HeaderMsg, Hint, QrScreen, TextScreen, TextScreenMsg, VerticalMenu,
        VerticalMenuScreen, VerticalMenuScreenMsg,
    },
    theme,
};

const TIMEOUT_MS: u32 = 2000;
const ITEM_PADDING: i16 = 16;
const GROUP_PADDING: i16 = 20;

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum GetAddress {
    Address,
    Confirmed,
    Menu,
    QrCode,
    AccountInfo,
    Cancel,
}

impl FlowController for GetAddress {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Address, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Address, FlowMsg::Confirmed) => Self::Confirmed.goto(),
            (Self::Confirmed, _) => self.return_msg(FlowMsg::Confirmed),
            (Self::Menu, FlowMsg::Choice(0)) => Self::QrCode.swipe_left(),
            (Self::Menu, FlowMsg::Choice(1)) => Self::AccountInfo.swipe_left(),
            (Self::Menu, FlowMsg::Choice(2)) => Self::Cancel.swipe_left(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Address.swipe_right(),
            (Self::QrCode, FlowMsg::Cancelled) => Self::Menu.goto(),
            (Self::AccountInfo, FlowMsg::Cancelled) => Self::Menu.goto(),
            (Self::Cancel, FlowMsg::Cancelled) => Self::Address.goto(),
            (Self::Cancel, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Cancelled),
            _ => self.do_nothing(),
        }
    }
}

#[allow(clippy::too_many_arguments)]
pub fn new_get_address(
    title: TString<'static>,
    _description: Option<TString<'static>>,
    extra: Option<TString<'static>>,
    address: Obj, // TODO: get rid of Obj
    chunkify: bool,
    address_qr: TString<'static>,
    case_sensitive: bool,
    account: Option<TString<'static>>,
    path: Option<TString<'static>>,
    _xpubs: Obj, // TODO: get rid of Obj
    title_success: TString<'static>,
    _br_code: u16,
    _br_name: TString<'static>,
) -> Result<SwipeFlow, error::Error> {
    // Address
    let flow_title: TString = TR::words__receive.into();
    let paragraphs = ConfirmValueParams {
        description: title,
        extra: extra.unwrap_or_else(|| "".into()),
        value: address.try_into()?,
        font: if chunkify {
            let address: TString = address.try_into()?;
            theme::get_chunkified_text_style(address.len())
        } else {
            &theme::TEXT_MONO_ADDRESS
        },
        description_font: &theme::TEXT_MEDIUM_EXTRA_LIGHT,
        extra_font: &theme::TEXT_SMALL,
    }
    .into_paragraphs()
    .with_placement(LinearPlacement::vertical().with_spacing(14));
    let content_address = TextScreen::new(paragraphs)
        .with_header(Header::new(flow_title).with_menu_button())
        .with_action_bar(ActionBar::new_single(
            Button::with_text(TR::buttons__confirm.into()).styled(theme::button_confirm()),
        ))
        .with_hint(Hint::new_instruction(
            TR::address__check_with_source,
            Some(theme::ICON_INFO),
        ))
        .map(|msg| match msg {
            TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
            TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
            TextScreenMsg::Menu => Some(FlowMsg::Info),
        });

    let content_confirmed =
        TextScreen::new(Paragraph::new(&theme::TEXT_REGULAR, title_success).into_paragraphs())
            .with_header(
                Header::new(TR::words__title_done.into())
                    .with_icon(theme::ICON_DONE, theme::GREEN_LIGHT)
                    .with_text_style(theme::label_title_confirm()),
            )
            .with_action_bar(ActionBar::new_timeout(
                Button::with_text(TR::instructions__continue_in_app.into()),
                TIMEOUT_MS,
            ))
            .map(|_| Some(FlowMsg::Confirmed));

    // Menu

    let content_menu = VerticalMenuScreen::new(
        VerticalMenu::empty()
            .item(
                Button::with_text(TR::address__qr_code.into())
                    .styled(theme::menu_item_title())
                    .with_text_align(Alignment::Start)
                    .with_content_offset(Offset::x(12)),
            )
            .item(
                Button::with_text(TR::address_details__account_info.into())
                    .styled(theme::menu_item_title())
                    .with_text_align(Alignment::Start)
                    .with_content_offset(Offset::x(12)),
            )
            .item(
                Button::with_text(TR::buttons__cancel.into())
                    .styled(theme::menu_item_title_orange())
                    .with_text_align(Alignment::Start)
                    .with_content_offset(Offset::x(12)),
            ),
    )
    .with_header(
        Header::new(flow_title)
            .with_right_button(Button::with_icon(theme::ICON_CROSS), HeaderMsg::Cancelled),
    )
    .map(|msg| match msg {
        VerticalMenuScreenMsg::Selected(i) => Some(FlowMsg::Choice(i)),
        VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
        _ => None,
    });

    // QrCode
    let content_qr = QrScreen::new(address_qr.map(|s| Qr::new(s, case_sensitive))?)
        .with_header(
            Header::new(TR::address_details__title_receive_address.into())
                .with_right_button(Button::with_icon(theme::ICON_CROSS), HeaderMsg::Cancelled),
        )
        .map(|_| Some(FlowMsg::Cancelled));

    // AccountInfo
    let mut para = ParagraphVecShort::new();
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
            .with_top_padding(GROUP_PADDING),
        );
        para.add(Paragraph::new(&theme::TEXT_MONO_EXTRA_LIGHT, p).with_top_padding(ITEM_PADDING));
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

    let content_cancel_info = TextScreen::new(
        Paragraph::new(&theme::TEXT_REGULAR, TR::address__cancel_receive)
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical()),
    )
    .with_header(Header::new(flow_title))
    .with_action_bar(ActionBar::new_double(
        Button::with_icon(theme::ICON_CHEVRON_LEFT),
        Button::with_text(TR::buttons__cancel.into()).styled(theme::button_cancel()),
    ))
    .with_hint(Hint::new_instruction(
        TR::address__cancel_contact_support,
        Some(theme::ICON_INFO),
    ))
    .map(|msg| match msg {
        TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
        TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
        _ => None,
    });

    let mut res = SwipeFlow::new(&GetAddress::Address)?;
    res.add_page(&GetAddress::Address, content_address)?
        .add_page(&GetAddress::Confirmed, content_confirmed)?
        .add_page(&GetAddress::Menu, content_menu)?
        .add_page(&GetAddress::QrCode, content_qr)?
        .add_page(&GetAddress::AccountInfo, content_account)?
        .add_page(&GetAddress::Cancel, content_cancel_info)?;
    Ok(res)
}
