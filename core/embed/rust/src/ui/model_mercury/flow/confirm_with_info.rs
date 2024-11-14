use crate::{
    error,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            swipe_detect::SwipeSettings,
            text::paragraphs::{ParagraphSource, ParagraphVecShort},
            ComponentExt,
        },
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

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmWithInfoSimple {
    Main,
    Menu,
}

impl FlowController for ConfirmWithInfoSimple {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }
    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Main, Direction::Left) => Self::Menu.swipe(direction),
            (Self::Main, Direction::Up) => self.return_msg(FlowMsg::Confirmed),
            (Self::Menu, Direction::Right) => Self::Main.swipe(direction),
            _ => self.do_nothing(),
        }
    }
    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Main, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Main.swipe_right(),
            (Self::Menu, FlowMsg::Choice(0)) => self.return_msg(FlowMsg::Info),
            (Self::Menu, FlowMsg::Choice(1)) => self.return_msg(FlowMsg::Cancelled),
            _ => self.do_nothing(),
        }
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmWithInfo {
    Main,
    Menu,
    Confirm,
}

impl FlowController for ConfirmWithInfo {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }
    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Main, Direction::Left) => Self::Menu.swipe(direction),
            (Self::Main, Direction::Up) => Self::Confirm.swipe(direction),
            (Self::Menu, Direction::Right) => Self::Main.swipe(direction),
            (Self::Confirm, Direction::Left) => Self::Menu.swipe(direction),
            (Self::Confirm, Direction::Down) => Self::Main.swipe(direction),
            _ => self.do_nothing(),
        }
    }
    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Main, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Main.swipe_right(),
            (Self::Menu, FlowMsg::Choice(0)) => self.return_msg(FlowMsg::Info),
            (Self::Menu, FlowMsg::Choice(1)) => self.return_msg(FlowMsg::Cancelled),
            (Self::Confirm, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Confirm, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            _ => self.do_nothing(),
        }
    }
}

pub fn new_confirm_with_info(
    title: TString<'static>,
    footer_description: Option<TString<'static>>,
    info_button: TString<'static>,
    paragraphs: ParagraphVecShort<'static>,
    prompt_title: Option<TString<'static>>,
) -> Result<SwipeFlow, error::Error> {
    let num_pages = if prompt_title.is_some() { 2 } else { 1 };
    let content_main = Frame::left_aligned(title, SwipeContent::new(paragraphs.into_paragraphs()))
        .with_menu_button()
        .with_footer(TR::instructions__swipe_up.into(), footer_description)
        .with_swipe(Direction::Up, SwipeSettings::default())
        .map(|msg| matches!(msg, FrameMsg::Button(FlowMsg::Info)).then_some(FlowMsg::Info))
        .with_pages(move |_| num_pages);

    let content_menu = Frame::left_aligned(
        TString::empty(),
        VerticalMenu::empty()
            .item(theme::ICON_CHEVRON_RIGHT, info_button)
            .danger(theme::ICON_CANCEL, TR::buttons__cancel.into()),
    )
    .with_cancel_button()
    .with_swipe(Direction::Right, SwipeSettings::immediate())
    .map(|msg| match msg {
        FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
        FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
    });

    if prompt_title.is_none() {
        SwipeFlow::new(&ConfirmWithInfoSimple::Main)?
            .with_page(&ConfirmWithInfoSimple::Main, content_main)?
            .with_page(&ConfirmWithInfoSimple::Menu, content_menu)
    } else {
        let content_confirm = Frame::left_aligned(
            prompt_title.unwrap(),
            SwipeContent::new(PromptScreen::new_hold_to_confirm()),
        )
        .with_footer(TR::instructions__hold_to_confirm.into(), None)
        .with_menu_button()
        .with_swipe(Direction::Down, SwipeSettings::default())
        .map(|msg| match msg {
            FrameMsg::Content(PromptMsg::Confirmed) => Some(FlowMsg::Confirmed),
            FrameMsg::Button(_) => Some(FlowMsg::Info),
            _ => Some(FlowMsg::Cancelled),
        });

        SwipeFlow::new(&ConfirmWithInfo::Main)?
            .with_page(&ConfirmWithInfo::Main, content_main)?
            .with_page(&ConfirmWithInfo::Menu, content_menu)?
            .with_page(&ConfirmWithInfo::Confirm, content_confirm)
    }
}
