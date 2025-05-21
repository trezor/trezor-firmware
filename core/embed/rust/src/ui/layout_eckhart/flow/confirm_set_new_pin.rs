use crate::{
    error,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            text::paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort, Paragraphs},
            ComponentExt as _,
        },
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::{Direction, LinearPlacement},
        layout_eckhart::firmware::TextScreenMsg,
    },
};

use super::super::{
    component::Button,
    firmware::{ActionBar, Header, TextScreen},
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum SetNewPin {
    Intro,
    CancelPin,
}

impl FlowController for SetNewPin {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, _direction: Direction) -> Decision {
        self.do_nothing()
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Intro, FlowMsg::Cancelled) => Self::CancelPin.goto(),
            (Self::Intro, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            (Self::CancelPin, FlowMsg::Cancelled) => Self::Intro.goto(),
            (Self::CancelPin, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            _ => self.do_nothing(),
        }
    }
}

pub fn new_set_new_pin(
    title: TString<'static>,
    description: TString<'static>,
) -> Result<SwipeFlow, error::Error> {
    let paragraphs = Paragraphs::new(Paragraph::new(&theme::firmware::TEXT_REGULAR, description))
        .with_placement(LinearPlacement::vertical());
    let content_intro = TextScreen::new(paragraphs)
        .with_header(Header::new(title))
        .with_action_bar(ActionBar::new_cancel_confirm())
        .map(|msg| match msg {
            TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
            TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
            _ => None,
        });

    let paragraphs_cancel_intro = ParagraphVecShort::from_iter([
        Paragraph::new(
            &theme::firmware::TEXT_REGULAR_WARNING,
            TR::words__not_recommended,
        ),
        Paragraph::new(&theme::firmware::TEXT_REGULAR, TR::pin__cancel_info),
    ])
    .into_paragraphs()
    .with_placement(LinearPlacement::vertical());

    let content_cancel_pin = TextScreen::new(paragraphs_cancel_intro)
        .with_header(Header::new(title))
        .with_action_bar(ActionBar::new_double(
            Button::with_icon(theme::ICON_CHEVRON_LEFT),
            Button::with_text(TR::buttons__continue.into()),
        ))
        .map(|msg| match msg {
            TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
            TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
            _ => None,
        });

    let mut res = SwipeFlow::new(&SetNewPin::Intro)?;
    res.add_page(&SetNewPin::Intro, content_intro)?
        .add_page(&SetNewPin::CancelPin, content_cancel_pin)?;
    Ok(res)
}
