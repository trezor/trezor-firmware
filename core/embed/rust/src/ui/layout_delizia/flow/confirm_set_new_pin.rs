use crate::{
    error,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            swipe_detect::SwipeSettings,
            text::paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort, Paragraphs},
        },
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::Direction,
    },
};

use super::super::{
    component::{Frame, PromptScreen, SwipeContent, VerticalMenu},
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum SetNewPin {
    Intro,
    Menu,
    CancelPinIntro,
    CancelPinConfirm,
}

impl FlowController for SetNewPin {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Intro, Direction::Left) => Self::Menu.swipe(direction),
            (Self::Intro, Direction::Up) => self.return_msg(FlowMsg::Confirmed),
            (Self::Menu, Direction::Right) => Self::Intro.swipe(direction),
            (Self::CancelPinIntro, Direction::Up) => Self::CancelPinConfirm.swipe(direction),
            (Self::CancelPinIntro, Direction::Right) => Self::Intro.swipe(direction),
            (Self::CancelPinConfirm, Direction::Down) => Self::CancelPinIntro.swipe(direction),
            (Self::CancelPinConfirm, Direction::Right) => Self::Intro.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Intro, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Choice(0)) => Self::CancelPinIntro.swipe_left(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Intro.swipe_right(),
            (Self::CancelPinIntro, FlowMsg::Cancelled) => Self::Intro.swipe_right(),
            (Self::CancelPinConfirm, FlowMsg::Cancelled) => Self::CancelPinIntro.swipe_right(),
            (Self::CancelPinConfirm, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Cancelled),
            _ => self.do_nothing(),
        }
    }
}

pub fn new_set_new_pin(
    title: TString<'static>,
    description: TString<'static>,
) -> Result<SwipeFlow, error::Error> {
    // TODO: supply more arguments for Wipe code setting when figma done
    let paragraphs = Paragraphs::new(Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, description));
    let content_intro = Frame::left_aligned(title, SwipeContent::new(paragraphs))
        .with_menu_button()
        .with_swipeup_footer(None)
        .with_swipe(Direction::Left, SwipeSettings::default())
        .map_to_button_msg();

    let content_menu = Frame::left_aligned(
        "".into(),
        VerticalMenu::empty().danger(theme::ICON_CANCEL, TR::pin__cancel_setup.into()),
    )
    .with_cancel_button()
    .with_swipe(Direction::Right, SwipeSettings::immediate())
    .map(super::util::map_to_choice);

    let paragraphs_cancel_intro = ParagraphVecShort::from_iter([
        Paragraph::new(&theme::TEXT_WARNING, TR::words__not_recommended),
        Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, TR::pin__cancel_info),
    ])
    .into_paragraphs();
    let content_cancel_intro = Frame::left_aligned(
        TR::pin__cancel_setup.into(),
        SwipeContent::new(paragraphs_cancel_intro),
    )
    .with_cancel_button()
    .with_swipeup_footer(Some(TR::pin__cancel_description.into()))
    .with_swipe(Direction::Right, SwipeSettings::immediate())
    .map_to_button_msg();

    let content_cancel_confirm = Frame::left_aligned(
        TR::pin__cancel_setup.into(),
        SwipeContent::new(PromptScreen::new_tap_to_cancel()),
    )
    .with_cancel_button()
    .with_footer(TR::instructions__tap_to_confirm.into(), None)
    .with_swipe(Direction::Down, SwipeSettings::default())
    .with_swipe(Direction::Right, SwipeSettings::immediate())
    .map(super::util::map_to_confirm);

    let mut res = SwipeFlow::new(&SetNewPin::Intro)?;
    res.add_page(&SetNewPin::Intro, content_intro)?
        .add_page(&SetNewPin::Menu, content_menu)?
        .add_page(&SetNewPin::CancelPinIntro, content_cancel_intro)?
        .add_page(&SetNewPin::CancelPinConfirm, content_cancel_confirm)?;
    Ok(res)
}
