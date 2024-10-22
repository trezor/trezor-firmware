use crate::{
    error,
    strutil::TString,
    translations::TR,
    ui::{
        component::{swipe_detect::SwipeSettings, CachedJpeg, ComponentExt},
        flow::{
            base::{Decision, DecisionBuilder},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::Direction,
        model_mercury::{
            component::{
                Frame, FrameMsg, PromptMsg, PromptScreen, SwipeContent, VerticalMenu,
                VerticalMenuChoiceMsg,
            },
            theme,
        },
    },
};

/// Flow for a setting of homescreen wallpaper showing a preview of the image,
/// menu to cancel and tap to confirm prompt.
#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmHomescreen {
    Homescreen,
    Menu,
    Confirm,
}

impl FlowController for ConfirmHomescreen {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Homescreen, Direction::Left) => Self::Menu.swipe(direction),
            (Self::Homescreen, Direction::Up) => Self::Confirm.swipe(direction),
            (Self::Menu, Direction::Right) => Self::Homescreen.swipe(direction),
            (Self::Confirm, Direction::Down) => Self::Homescreen.swipe(direction),
            (Self::Confirm, Direction::Left) => Self::Menu.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Homescreen, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Homescreen.swipe_right(),
            (Self::Menu, FlowMsg::Choice(0)) => self.return_msg(FlowMsg::Cancelled),
            (Self::Confirm, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            (Self::Confirm, FlowMsg::Info) => Self::Menu.goto(),
            _ => self.do_nothing(),
        }
    }
}

pub fn new_confirm_homescreen(
    title: TString<'static>,
    image: CachedJpeg,
) -> Result<SwipeFlow, error::Error> {
    let content_homescreen = Frame::left_aligned(title, SwipeContent::new(image))
        .with_menu_button()
        .with_footer(
            TR::instructions__swipe_up.into(),
            Some(TR::buttons__change.into()),
        )
        .with_swipe(Direction::Up, SwipeSettings::default())
        // Homescreen + Tap to confirm
        .with_pages(|_| 2)
        .map(|msg| match msg {
            FrameMsg::Button(_) => Some(FlowMsg::Info),
            _ => None,
        });

    let content_menu = Frame::left_aligned(
        TString::empty(),
        VerticalMenu::empty().danger(theme::ICON_CANCEL, TR::buttons__cancel.into()),
    )
    .with_cancel_button()
    .with_swipe(Direction::Right, SwipeSettings::immediate())
    .map(|msg| match msg {
        FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
        FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
    });

    let content_confirm = Frame::left_aligned(
        TR::homescreen__title_set.into(),
        SwipeContent::new(PromptScreen::new_tap_to_confirm()),
    )
    .with_menu_button()
    .with_footer(TR::instructions__tap_to_confirm.into(), None)
    .with_swipe(Direction::Down, SwipeSettings::default())
    .with_swipe(Direction::Left, SwipeSettings::default())
    .map(|msg| match msg {
        FrameMsg::Content(PromptMsg::Confirmed) => Some(FlowMsg::Confirmed),
        FrameMsg::Button(_) => Some(FlowMsg::Info),
        _ => None,
    });

    let res = SwipeFlow::new(&ConfirmHomescreen::Homescreen)?
        .with_page(&ConfirmHomescreen::Homescreen, content_homescreen)?
        .with_page(&ConfirmHomescreen::Menu, content_menu)?
        .with_page(&ConfirmHomescreen::Confirm, content_confirm)?;
    Ok(res)
}
