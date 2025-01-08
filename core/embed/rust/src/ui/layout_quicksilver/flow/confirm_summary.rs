use heapless::Vec;

use crate::{
    error::{self},
    maybe_trace::MaybeTrace,
    strutil::TString,
    translations::TR,
    ui::{
        component::{swipe_detect::SwipeSettings, Component, ComponentExt},
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, Swipable, SwipeFlow,
        },
        geometry::Direction,
    },
};

use super::{
    super::{
        component::{
            Frame, FrameMsg, PromptMsg, PromptScreen, SwipeContent, VerticalMenu,
            VerticalMenuChoiceMsg,
        },
        theme,
    },
    util::ShowInfoParams,
};

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
            (Self::Summary | Self::Hold, Direction::Left) => Self::Menu.swipe(direction),
            (Self::Summary, Direction::Up) => Self::Hold.swipe(direction),
            (Self::Hold, Direction::Down) => Self::Summary.swipe(direction),
            (Self::Menu, Direction::Right) => Self::Summary.swipe(direction),
            (Self::ExtraInfo | Self::AccountInfo | Self::CancelTap, Direction::Right) => {
                Self::Menu.swipe(direction)
            }
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

fn dummy_page() -> impl Component<Msg = FlowMsg> + Swipable + MaybeTrace {
    Frame::left_aligned(TString::empty(), VerticalMenu::empty()).map(|_| Some(FlowMsg::Cancelled))
}

pub fn new_confirm_summary(
    summary_params: ShowInfoParams,
    account_params: Option<ShowInfoParams>,
    extra_params: Option<ShowInfoParams>,
    extra_title: Option<TString<'static>>,
    verb_cancel: Option<TString<'static>>,
) -> Result<SwipeFlow, error::Error> {
    // Summary
    let content_summary = summary_params
        .into_layout()?
        // Summary(1) + Hold(1)
        .with_pages(|summary_pages| summary_pages + 1);

    // Hold to confirm
    let content_hold = Frame::left_aligned(
        TR::send__sign_transaction.into(),
        SwipeContent::new(PromptScreen::new_hold_to_confirm()),
    )
    .with_menu_button()
    .with_footer(TR::instructions__hold_to_sign.into(), None)
    .with_swipe(Direction::Down, SwipeSettings::default())
    .with_swipe(Direction::Left, SwipeSettings::default())
    .map(|msg| match msg {
        FrameMsg::Content(PromptMsg::Confirmed) => Some(FlowMsg::Confirmed),
        FrameMsg::Button(_) => Some(FlowMsg::Info),
        _ => None,
    });

    // ExtraInfo
    let content_extra = extra_params
        .map(|params| params.into_layout())
        .transpose()?;
    // AccountInfo
    let content_account = account_params
        .map(|params| params.into_layout())
        .transpose()?;

    // Menu with provided info and cancel
    let mut menu = VerticalMenu::empty();
    let mut menu_items = Vec::<usize, 3>::new();
    if content_extra.is_some() {
        menu = menu.item(
            theme::ICON_CHEVRON_RIGHT,
            extra_title.unwrap_or(TR::buttons__more_info.into()),
        );
        unwrap!(menu_items.push(MENU_ITEM_EXTRA_INFO));
    }
    if content_account.is_some() {
        menu = menu.item(
            theme::ICON_CHEVRON_RIGHT,
            TR::address_details__account_info.into(),
        );
        unwrap!(menu_items.push(MENU_ITEM_ACCOUNT_INFO));
    }
    menu = menu.danger(
        theme::ICON_CANCEL,
        verb_cancel.unwrap_or(TR::send__cancel_sign.into()),
    );
    unwrap!(menu_items.push(MENU_ITEM_CANCEL));
    let content_menu = Frame::left_aligned(TString::empty(), menu)
        .with_cancel_button()
        .with_swipe(Direction::Right, SwipeSettings::immediate())
        .map(move |msg| match msg {
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => {
                let selected_item = menu_items[i];
                Some(FlowMsg::Choice(selected_item))
            }
            FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
        });

    // CancelTap
    let content_cancel_tap = Frame::left_aligned(
        TR::send__cancel_sign.into(),
        PromptScreen::new_tap_to_cancel(),
    )
    .with_cancel_button()
    .with_footer(TR::instructions__tap_to_confirm.into(), None)
    .with_swipe(Direction::Right, SwipeSettings::immediate())
    .map(|msg| match msg {
        FrameMsg::Content(PromptMsg::Confirmed) => Some(FlowMsg::Confirmed),
        FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
        _ => None,
    });

    let mut res = SwipeFlow::new(&ConfirmSummary::Summary)?
        .with_page(&ConfirmSummary::Summary, content_summary)?
        .with_page(&ConfirmSummary::Hold, content_hold)?
        .with_page(&ConfirmSummary::Menu, content_menu)?;
    if let Some(content_extra) = content_extra {
        res = res.with_page(&ConfirmSummary::ExtraInfo, content_extra)?
    } else {
        res = res.with_page(&ConfirmSummary::ExtraInfo, dummy_page())?
    };
    if let Some(content_account) = content_account {
        res = res.with_page(&ConfirmSummary::AccountInfo, content_account)?
    } else {
        res = res.with_page(&ConfirmSummary::AccountInfo, dummy_page())?
    };
    res = res.with_page(&ConfirmSummary::CancelTap, content_cancel_tap)?;

    Ok(res)
}
