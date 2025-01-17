use crate::{
    error,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            swipe_detect::SwipeSettings,
            text::paragraphs::{Paragraph, ParagraphSource},
            ComponentExt,
        },
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::Direction,
    },
};

use super::super::{
    component::{Frame, FrameMsg, StatusScreen, SwipeContent, VerticalMenu, VerticalMenuChoiceMsg},
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ShowDanger {
    Message,
    Menu,
    Cancelled,
}

impl FlowController for ShowDanger {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Message, Direction::Left) => Self::Menu.swipe(direction),
            (Self::Message, Direction::Up) => Self::Cancelled.swipe(direction),
            (Self::Menu, Direction::Right) => Self::Message.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Message, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Choice(1)) => self.return_msg(FlowMsg::Confirmed),
            (Self::Menu, FlowMsg::Choice(_)) => Self::Cancelled.swipe_up(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Message.swipe_right(),
            (Self::Cancelled, _) => self.return_msg(FlowMsg::Cancelled),
            _ => self.do_nothing(),
        }
    }
}

const EXTRA_PADDING: i16 = 6;

pub fn new_show_danger(
    title: TString<'static>,
    description: TString<'static>,
    value: TString<'static>,
    verb_cancel: Option<TString<'static>>,
) -> Result<SwipeFlow, error::Error> {
    let confirm: TString = TR::words__continue_anyway.into();
    let done_title: TString = TR::words__operation_cancelled.into();

    let verb_cancel = verb_cancel.unwrap_or(TR::words__cancel_and_exit.into());

    // Message
    let paragraphs = [
        Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, description),
        Paragraph::new(&theme::TEXT_MAIN_GREY_EXTRA_LIGHT, value).with_top_padding(EXTRA_PADDING),
    ]
    .into_paragraphs();
    let content_message = Frame::left_aligned(title, SwipeContent::new(paragraphs))
        .with_menu_button()
        .with_footer(TR::instructions__swipe_up.into(), Some(verb_cancel))
        .with_danger()
        .with_swipe(Direction::Up, SwipeSettings::default())
        .with_swipe(Direction::Left, SwipeSettings::default())
        .map(|msg| matches!(msg, FrameMsg::Button(_)).then_some(FlowMsg::Info));
    // .one_button_request(ButtonRequestCode::Warning, br_name);

    // Menu
    let content_menu = Frame::left_aligned(
        "".into(),
        VerticalMenu::empty()
            .item(theme::ICON_CANCEL, verb_cancel)
            .danger(theme::ICON_CHEVRON_RIGHT, confirm),
    )
    .with_cancel_button()
    .with_swipe(Direction::Right, SwipeSettings::immediate())
    .map(|msg| match msg {
        FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
        FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
    });

    // Cancelled
    let content_cancelled = Frame::left_aligned(
        TR::words__title_done.into(),
        StatusScreen::new_neutral_timeout(done_title),
    )
    .with_footer(TR::instructions__continue_in_app.into(), None)
    .with_result_icon(theme::ICON_BULLET_CHECKMARK, theme::GREY_DARK)
    .map(|_| Some(FlowMsg::Cancelled));

    let res = SwipeFlow::new(&ShowDanger::Message)?
        .with_page(&ShowDanger::Message, content_message)?
        .with_page(&ShowDanger::Menu, content_menu)?
        .with_page(&ShowDanger::Cancelled, content_cancelled)?;
    Ok(res)
}
