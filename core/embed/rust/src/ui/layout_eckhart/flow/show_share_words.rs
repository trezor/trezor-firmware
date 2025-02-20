use crate::{
    error,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            text::paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort},
            ComponentExt,
        },
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::{Direction, LinearPlacement},
    },
};

use heapless::Vec;

use super::super::{
    component::Button,
    firmware::{
        ActionBar, Header, ShareWordsScreen, ShareWordsScreenMsg, TextScreen, TextScreenMsg,
    },
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ShowShareWords {
    Instruction,
    ShareWords,
    Confirm,
    CheckBackupIntro,
}

impl FlowController for ShowShareWords {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Instruction, FlowMsg::Cancelled) => self.return_msg(FlowMsg::Cancelled),
            (Self::Instruction, FlowMsg::Confirmed) => Self::ShareWords.goto(),
            (Self::ShareWords, FlowMsg::Cancelled) => Self::Instruction.goto(),
            (Self::ShareWords, FlowMsg::Confirmed) => Self::Confirm.goto(),
            (Self::Confirm, FlowMsg::Cancelled) => Self::ShareWords.goto(),
            (Self::Confirm, FlowMsg::Confirmed) => Self::CheckBackupIntro.goto(),
            (Self::CheckBackupIntro, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            _ => self.do_nothing(),
        }
    }
}

pub fn new_show_share_words_flow(
    words: Vec<TString<'static>, 33>,
    _subtitle: TString<'static>,
    instructions_paragraphs: ParagraphVecShort<'static>,
    text_confirm: TString<'static>,
) -> Result<SwipeFlow, error::Error> {
    let instruction = TextScreen::new(
        instructions_paragraphs
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical().with_spacing(24)),
    )
    .with_header(Header::new(TR::reset__recovery_wallet_backup_title.into()))
    .with_action_bar(ActionBar::new_single(Button::with_text(
        TR::buttons__continue.into(),
    )))
    .map(|msg| match msg {
        TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
        TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
        _ => Some(FlowMsg::Cancelled),
    });

    let share_words = ShareWordsScreen::new(words).map(|msg| match msg {
        ShareWordsScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
        ShareWordsScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
    });

    let confirm_paragraphs = Paragraph::new(&theme::TEXT_REGULAR, text_confirm)
        .into_paragraphs()
        .with_placement(LinearPlacement::vertical());

    let confirm = TextScreen::new(confirm_paragraphs)
        .with_header(Header::new(TR::reset__recovery_wallet_backup_title.into()))
        .with_action_bar(ActionBar::new_double(
            Button::with_icon(theme::ICON_CHEVRON_UP),
            Button::with_text(TR::buttons__hold_to_confirm.into())
                .styled(theme::button_confirm())
                .with_long_press(theme::CONFIRM_HOLD_DURATION),
        ))
        .map(|msg| match msg {
            TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
            TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
            TextScreenMsg::Menu => Some(FlowMsg::Cancelled),
        });

    let check_backup_paragraphs =
        Paragraph::new(&theme::TEXT_REGULAR, TR::reset__check_backup_instructions)
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical());

    let check_backup_intro = TextScreen::new(check_backup_paragraphs)
        .with_header(Header::new(TR::reset__check_wallet_backup_title.into()))
        .with_action_bar(ActionBar::new_single(Button::with_text(
            TR::buttons__continue.into(),
        )))
        .map(|msg| match msg {
            TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
            _ => None,
        });

    let mut res = SwipeFlow::new(&ShowShareWords::Instruction)?;
    res.add_page(&ShowShareWords::Instruction, instruction)?
        .add_page(&ShowShareWords::ShareWords, share_words)?
        .add_page(&ShowShareWords::Confirm, confirm)?
        .add_page(&ShowShareWords::CheckBackupIntro, check_backup_intro)?;
    Ok(res)
}
