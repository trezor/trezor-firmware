use crate::{
    error,
    strutil::TString,
    trezorhal::model,
    ui::{
        component::{swipe_detect::SwipeSettings, ComponentExt, EventCtx, SwipeDirection},
        flow::{
            base::{DecisionBuilder as _, StateChange},
            FlowMsg, FlowState, SwipeFlow, SwipePage,
        },
    },
};

use super::super::component::{
    Footer, Frame, FrameMsg, Homescreen, HomescreenMsg, InternallySwipable, PagedVerticalMenu,
    SwipeContent, VerticalMenuChoiceMsg,
};

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
            (Self::Menu, FlowMsg::Choice(0)) => self.return_msg(FlowMsg::Choice(0)),
            (Self::Menu, FlowMsg::Choice(1)) => self.return_msg(FlowMsg::Choice(1)),
            (Self::Menu, FlowMsg::Choice(2)) => self.return_msg(FlowMsg::Choice(2)),
            (Self::Menu, FlowMsg::Choice(3)) => self.return_msg(FlowMsg::Choice(3)),
            _ => self.do_nothing(),
        }
    }
}

const DEMO_OPTIONS: &[&str] = &[
    "Start tutorial",
    "Set up a Wallet",
    "Send Bitcoin",
    "Recovery",
];

fn footer_update_fn(
    content: &SwipeContent<SwipePage<PagedVerticalMenu<impl Fn(usize) -> TString<'static>>>>,
    ctx: &mut EventCtx,
    footer: &mut Footer,
) {
    let current_page = content.inner().inner().current_page();
    let total_pages = content.inner().inner().num_pages();
    footer.update_page_counter(ctx, current_page, Some(total_pages));
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
        let label_fn =
            move |page_index: usize| -> TString<'static> { DEMO_OPTIONS[page_index].into() };

        let content_menu = Frame::left_aligned(
            "".into(),
            SwipeContent::new(SwipePage::vertical(PagedVerticalMenu::new(
                DEMO_OPTIONS.len(),
                label_fn,
            ))),
        )
        .with_cancel_button()
        .with_footer_page_hint(
            "More options".into(),
            "".into(),
            "Swipe up".into(),
            "Swipe down".into(),
        )
        .register_footer_update_fn(footer_update_fn)
        .with_swipe(SwipeDirection::Down, SwipeSettings::default())
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .with_vertical_pages()
        .map(|msg| match msg {
            FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
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
