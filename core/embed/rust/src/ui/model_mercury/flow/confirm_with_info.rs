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
            component::{Frame, FrameMsg, SwipeContent, VerticalMenu, VerticalMenuChoiceMsg},
            theme,
        },
    },
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmWithInfo {
    Main,
    Menu,
}

impl FlowController for ConfirmWithInfo {
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

pub fn new_confirm_with_info(
    title: TString<'static>,
    button: TString<'static>,
    info_button: TString<'static>,
    paragraphs: ParagraphVecShort<'static>,
) -> Result<SwipeFlow, error::Error> {
    let content_main = Frame::left_aligned(title, SwipeContent::new(paragraphs.into_paragraphs()))
        .with_menu_button()
        .with_footer(TR::instructions__swipe_up.into(), Some(button))
        .with_swipe(Direction::Up, SwipeSettings::default())
        .map(|msg| matches!(msg, FrameMsg::Button(FlowMsg::Info)).then_some(FlowMsg::Info));

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

    SwipeFlow::new(&ConfirmWithInfo::Main)?
        .with_page(&ConfirmWithInfo::Main, content_main)?
        .with_page(&ConfirmWithInfo::Menu, content_menu)
}
