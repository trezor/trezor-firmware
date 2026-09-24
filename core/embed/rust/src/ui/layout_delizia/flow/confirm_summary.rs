use heapless::Vec;

use super::super::component::{
    Frame, Header, PromptScreen, SwipeContent, VerticalMenu, VerticalMenuChoiceMsg,
};
use super::super::theme;
use super::util::{dummy_page, ShowInfoScreen};
use crate::micropython::Error;
use crate::strutil::TString;
use crate::translations::TR;
use crate::ui::component::swipe_detect::SwipeSettings;
use crate::ui::component::text::paragraphs::{
    Paragraph, ParagraphSource, ParagraphVecLong, VecExt,
};
use crate::ui::component::ComponentExt;
use crate::ui::flow::base::{Decision, DecisionBuilder as _};
use crate::ui::flow::{FlowController, FlowMsg, SwipeFlow, SwipePage};
use crate::ui::geometry::Direction;

const MENU_ITEM_CANCEL: usize = 0;
const MENU_ITEM_EXTRA_INFO: usize = 1;
const MENU_ITEM_ACCOUNT_INFO: usize = 2;

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmSummary {
    Summary,
    Hold,
    Menu,
    ExtraInfo,
    AccountInfo,
    CancelTap,
}

impl FlowController for ConfirmSummary {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Summary, Direction::Down) => self.return_msg(FlowMsg::Back),
            (Self::Summary, Direction::Up) => Self::Hold.swipe(direction),
            (Self::Hold, Direction::Down) => Self::Summary.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (_, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Hold, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_CANCEL)) => Self::CancelTap.swipe_left(),
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_EXTRA_INFO)) => Self::ExtraInfo.swipe_left(),
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_ACCOUNT_INFO)) => Self::AccountInfo.swipe_left(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Summary.swipe_right(),
            (Self::CancelTap, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Cancelled),
            (_, FlowMsg::Cancelled) => Self::Menu.goto(),
            _ => self.do_nothing(),
        }
    }
}

#[allow(clippy::too_many_arguments)]
pub fn new_confirm_summary(
    title: TString<'static>,
    amount: Option<TString<'static>>,
    amount_label: Option<TString<'static>>,
    fee: TString<'static>,
    fee_label: TString<'static>,
    account_info: Option<ShowInfoScreen>,
    account_title: Option<TString<'static>>,
    extra_info: Option<ShowInfoScreen>,
    extra_title: Option<TString<'static>>,
    verb_cancel: Option<TString<'static>>,
    can_go_back: bool,
) -> Result<SwipeFlow, Error> {
    // Summary
    let mut summary_paragraphs = ParagraphVecLong::new();
    if let (Some(amount_label), Some(amount)) = (amount_label, amount) {
        summary_paragraphs.add(Paragraph::new(&theme::TEXT_SUB_GREY, amount_label).no_break());
        summary_paragraphs.add(Paragraph::new(&theme::TEXT_MONO_GREY_LIGHT, amount));
        summary_paragraphs.add(Paragraph::new::<TString<'static>>(
            &theme::TEXT_SUB_GREY,
            " ".into(),
        ));
    }
    summary_paragraphs.add(Paragraph::new(&theme::TEXT_SUB_GREY, fee_label).no_break());
    summary_paragraphs.add(Paragraph::new(&theme::TEXT_MONO_GREY_LIGHT, fee));

    let mut summary_frame = Frame::with_header(
        Header::left_aligned(title).with_menu_button(),
        SwipeContent::new(SwipePage::vertical(summary_paragraphs.into_paragraphs())),
    )
    .with_footer(TR::instructions__tap_to_continue.into(), None)
    .with_swipe(Direction::Up, SwipeSettings::Default)
    .with_flow_menu();
    if can_go_back {
        summary_frame = summary_frame.with_swipe(Direction::Down, SwipeSettings::Default);
    }
    let content_summary = summary_frame
        .with_vertical_pages()
        .map_to_button_msg()
        // Summary(1) + Hold(1)
        .with_pages(|summary_pages| summary_pages + 1);

    // Hold to confirm
    let content_hold = Frame::with_header(
        Header::left_aligned(TR::send__sign_transaction.into()).with_menu_button(),
        SwipeContent::new(PromptScreen::new_hold_to_confirm()),
    )
    .with_flow_menu()
    .with_footer(TR::instructions__hold_to_sign.into(), None)
    .with_swipe(Direction::Down, SwipeSettings::Default)
    .map(super::util::map_to_confirm);

    // Menu with provided info and cancel
    let mut menu = VerticalMenu::empty();
    let mut menu_items = Vec::<usize, 3>::new();
    if extra_info.is_some() {
        menu = menu.item(
            theme::ICON_CHEVRON_RIGHT,
            extra_title.unwrap_or(TR::buttons__more_info.into()),
        );
        unwrap!(menu_items.push(MENU_ITEM_EXTRA_INFO));
    }
    if account_info.is_some() {
        menu = menu.item(
            theme::ICON_CHEVRON_RIGHT,
            account_title.unwrap_or(TR::address_details__account_info.into()),
        );
        unwrap!(menu_items.push(MENU_ITEM_ACCOUNT_INFO));
    }
    menu = menu.cancel_item(verb_cancel.unwrap_or(TR::buttons__cancel_sign.into()));
    unwrap!(menu_items.push(MENU_ITEM_CANCEL));
    let content_menu = Frame::with_header(
        Header::left_aligned(TString::empty()).with_cancel_button(),
        menu,
    )
    .map(move |msg| match msg {
        VerticalMenuChoiceMsg::Selected(i) => {
            let selected_item = menu_items[i];
            Some(FlowMsg::Choice(selected_item))
        }
    });

    // CancelTap
    let content_cancel_tap = Frame::with_header(
        Header::left_aligned(TR::send__cancel_sign.into()).with_cancel_button(),
        PromptScreen::new_tap_to_cancel(),
    )
    .with_footer(TR::instructions__tap_to_confirm.into(), None)
    .map(super::util::map_to_confirm);

    let mut res = SwipeFlow::new(&ConfirmSummary::Summary);
    res.add_page(&ConfirmSummary::Summary, content_summary)?
        .add_page(&ConfirmSummary::Hold, content_hold)?
        .add_page(&ConfirmSummary::Menu, content_menu)?;
    if let Some(content_extra) = extra_info {
        res.add_page(&ConfirmSummary::ExtraInfo, content_extra)?;
    } else {
        res.add_page(&ConfirmSummary::ExtraInfo, dummy_page())?;
    };
    if let Some(content_account) = account_info {
        res.add_page(&ConfirmSummary::AccountInfo, content_account)?;
    } else {
        res.add_page(&ConfirmSummary::AccountInfo, dummy_page())?;
    };
    res.add_page(&ConfirmSummary::CancelTap, content_cancel_tap)?;

    Ok(res)
}
