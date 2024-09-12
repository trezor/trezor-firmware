use crate::{
    error,
    strutil::TString,
    trezorhal::model,
    ui::{
        component::{swipe_detect::SwipeSettings, ComponentExt, SwipeDirection},
        flow::{
            base::{DecisionBuilder as _, StateChange},
            FlowMsg, FlowState, SwipeFlow,
        },
    },
};

use super::super::component::{
    Frame, FrameMsg, Homescreen, HomescreenMsg, VerticalMenu, VerticalMenuChoiceMsg,
};
use super::super::theme;

#[derive(Copy, Clone, ToPrimitive)]
pub enum HomescreenFlow {
    Homescreen,
    Menu,
}

impl FlowState for HomescreenFlow {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: SwipeDirection) -> StateChange {
        match (self, direction) {
            (Self::Homescreen, SwipeDirection::Left) => Self::Menu.swipe(direction),
            (Self::Menu, SwipeDirection::Right) => Self::Homescreen.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> StateChange {
        match (self, msg) {
            (Self::Homescreen, FlowMsg::Info) => Self::Menu.transit(),
            (Self::Homescreen, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            (Self::Homescreen, FlowMsg::Cancelled) => self.return_msg(FlowMsg::Cancelled),
            (Self::Menu, FlowMsg::Cancelled) => Self::Homescreen.swipe_right(),
            _ => self.do_nothing(),
        }
    }
}

impl HomescreenFlow {
    pub fn new_homescreen_flow(
        label: Option<TString<'static>>,
        notification: Option<TString<'static>>,
        notification_level: u8,
        notification_clickable: bool,
        hold: bool,
    ) -> Result<SwipeFlow, error::Error> {
        let label = label.unwrap_or_else(|| model::FULL_NAME.into());
        let notification = notification.map(|w| (w, notification_level));

        let content_menu =
            VerticalMenu::empty().item(theme::ICON_CHEVRON_RIGHT, "Set brightness".into());
        let content_menu = Frame::left_aligned("".into(), content_menu)
            .with_cancel_button()
            .with_swipe(SwipeDirection::Down, SwipeSettings::default())
            .with_swipe(SwipeDirection::Left, SwipeSettings::default())
            .map(|msg| match msg {
                FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
                FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
            });
        let content_homescreen = Homescreen::new(label, notification, hold, notification_clickable)
            .map(|msg| match msg {
                HomescreenMsg::Dismissed => Some(FlowMsg::Cancelled),
                HomescreenMsg::MenuClicked => Some(FlowMsg::Info),
                HomescreenMsg::NotificationClicked => Some(FlowMsg::Confirmed),
            });

        SwipeFlow::new(&HomescreenFlow::Homescreen)?
            .with_page(&HomescreenFlow::Homescreen, content_homescreen)?
            .with_page(&HomescreenFlow::Menu, content_menu)
    }
}
