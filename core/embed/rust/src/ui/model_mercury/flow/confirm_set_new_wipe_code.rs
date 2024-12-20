use crate::{
    error,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            swipe_detect::SwipeSettings,
            text::paragraphs::{Paragraph, Paragraphs},
            ComponentExt,
        },
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::Direction,
        model_mercury::component::SwipeContent,
    },
};

use super::super::{
    component::{Frame, FrameMsg, VerticalMenu, VerticalMenuChoiceMsg},
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum SetNewWipeCode {
    Intro,
    Menu,
}

impl FlowController for SetNewWipeCode {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Intro, Direction::Left) => Self::Menu.swipe(direction),
            (Self::Intro, Direction::Up) => self.return_msg(FlowMsg::Confirmed),
            (Self::Menu, Direction::Right) => Self::Intro.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Intro, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Choice(0)) => self.return_msg(FlowMsg::Cancelled),
            (Self::Menu, FlowMsg::Cancelled) => self.return_msg(FlowMsg::Cancelled),
            _ => self.do_nothing(),
        }
    }
}

pub fn new_set_new_wipe_code(
    title: TString<'static>,
    description: TString<'static>,
    cancel_title: TString<'static>,
) -> Result<SwipeFlow, error::Error> {
    let paragraphs = Paragraphs::new(Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, description));
    let content_intro = Frame::left_aligned(title, SwipeContent::new(paragraphs))
        .with_menu_button()
        .with_footer(TR::instructions__swipe_up.into(), None)
        .with_swipe(Direction::Up, SwipeSettings::default())
        .with_subtitle(TR::words__settings.into())
        .with_swipe(Direction::Left, SwipeSettings::default())
        .map(|msg| match msg {
            FrameMsg::Button(bm) => Some(bm),
            _ => None,
        });

    let content_menu = Frame::left_aligned(
        "".into(),
        VerticalMenu::empty().danger(theme::ICON_CANCEL, cancel_title),
    )
    .with_cancel_button()
    .with_swipe(Direction::Right, SwipeSettings::immediate())
    .map(|msg| match msg {
        FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
        FrameMsg::Button(FlowMsg::Cancelled) => Some(FlowMsg::Cancelled),
        FrameMsg::Button(_) => None,
    });

    let res = SwipeFlow::new(&SetNewWipeCode::Intro)?
        .with_page(&SetNewWipeCode::Intro, content_intro)?
        .with_page(&SetNewWipeCode::Menu, content_menu)?;
    Ok(res)
}
