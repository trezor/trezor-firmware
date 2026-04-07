use crate::{
    error,
    strutil::{ShortString, TString},
    translations::TR,
    ui::{
        component::{
            text::paragraphs::{Paragraph, ParagraphSource},
            ComponentExt,
        },
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::{Direction, LinearPlacement},
    },
};

use super::super::{
    component::Button,
    firmware::{
        ActionBar, Header, PassphraseInput, StringKeyboard, StringKeyboardMsg, TextScreen,
        TextScreenMsg,
    },
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum RequestPassphrase {
    Keypad,
    ConfirmEmpty,
}

impl FlowController for RequestPassphrase {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, _direction: Direction) -> Decision {
        self.do_nothing()
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Keypad, FlowMsg::Text(s)) => {
                if s.is_empty() {
                    Self::ConfirmEmpty.goto()
                } else {
                    self.return_msg(FlowMsg::Text(s))
                }
            }
            (Self::Keypad, FlowMsg::Cancelled) => self.return_msg(FlowMsg::Cancelled),
            (Self::ConfirmEmpty, FlowMsg::Cancelled) => Self::Keypad.goto(),
            (Self::ConfirmEmpty, FlowMsg::Confirmed) => {
                self.return_msg(FlowMsg::Text(ShortString::new()))
            }
            _ => self.do_nothing(),
        }
    }
}

pub fn new_request_passphrase(
    prompt: TString<'static>,
    prompt_empty: TString<'static>,
    max_len: usize,
) -> Result<SwipeFlow, error::Error> {
    let content_confirm_empty = TextScreen::new(
        Paragraph::new(&theme::TEXT_REGULAR, prompt_empty)
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical()),
    )
    .with_header(Header::new(prompt))
    .with_action_bar(ActionBar::new_double(
        Button::with_icon(theme::ICON_CHEVRON_LEFT),
        Button::with_text(TR::buttons__confirm.into()),
    ))
    .with_page_limit(1)
    .map(|msg| match msg {
        TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
        TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
        _ => Some(FlowMsg::Cancelled),
    });

    let input = PassphraseInput::new(max_len, false, true);
    let content_keypad = StringKeyboard::new(prompt, input).map(|msg| match msg {
        StringKeyboardMsg::Confirmed(s) => Some(FlowMsg::Text(s)),
        StringKeyboardMsg::Cancelled => Some(FlowMsg::Cancelled),
    });

    let mut res = SwipeFlow::new(&RequestPassphrase::Keypad)?;
    res.add_page(&RequestPassphrase::Keypad, content_keypad)?
        .add_page(&RequestPassphrase::ConfirmEmpty, content_confirm_empty)?;
    Ok(res)
}
