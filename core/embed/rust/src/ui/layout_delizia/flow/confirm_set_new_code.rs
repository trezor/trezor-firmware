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
pub enum SetNewCode {
    Intro,
    Menu,
    CancelIntro,
    CancelConfirm,
}

impl FlowController for SetNewCode {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Intro, Direction::Up) => self.return_msg(FlowMsg::Confirmed),
            (Self::CancelIntro, Direction::Up) => Self::CancelConfirm.swipe(direction),
            (Self::CancelConfirm, Direction::Down) => Self::CancelIntro.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Intro, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Choice(0)) => Self::CancelIntro.swipe_left(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Intro.swipe_right(),
            (Self::CancelIntro, FlowMsg::Cancelled) => Self::Intro.swipe_right(),
            (Self::CancelConfirm, FlowMsg::Cancelled) => Self::CancelIntro.swipe_right(),
            (Self::CancelConfirm, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Cancelled),
            _ => self.do_nothing(),
        }
    }
}

pub fn new_set_new_code(
    title: TString<'static>,
    description: TString<'static>,
    _is_wipe_code: bool,
) -> Result<SwipeFlow, error::Error> {
    let paragraphs = Paragraphs::new(Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, description));
    let content_intro = Frame::left_aligned(title, SwipeContent::new(paragraphs))
        .with_menu_button()
        .with_swipeup_footer(None)
        .map_to_button_msg();

    let content_menu = Frame::left_aligned(
        "".into(),
        VerticalMenu::empty().danger(theme::ICON_CANCEL, TR::pin__cancel_setup.into()),
    )
    .with_cancel_button()
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
    .map_to_button_msg();

    let content_cancel_confirm = Frame::left_aligned(
        TR::pin__cancel_setup.into(),
        SwipeContent::new(PromptScreen::new_tap_to_cancel()),
    )
    .with_cancel_button()
    .with_footer(TR::instructions__tap_to_confirm.into(), None)
    .with_swipe(Direction::Down, SwipeSettings::Default)
    .map(super::util::map_to_confirm);

    let mut res = SwipeFlow::new(&SetNewCode::Intro)?;
    res.add_page(&SetNewCode::Intro, content_intro)?
        .add_page(&SetNewCode::Menu, content_menu)?
        .add_page(&SetNewCode::CancelIntro, content_cancel_intro)?
        .add_page(&SetNewCode::CancelConfirm, content_cancel_confirm)?;
    Ok(res)
}
