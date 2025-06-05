use crate::{
    error,
    strutil::TString,
    translations::TR,
    ui::{
        button_request::{ButtonRequest, ButtonRequestCode},
        component::{
            text::paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort},
            ButtonRequestExt, ComponentExt,
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
        ActionBar, Header, ShareWordsScreen, ShareWordsScreenMsg, ShortMenuVec, TextScreen,
        TextScreenMsg, VerticalMenu, VerticalMenuScreen, VerticalMenuScreenMsg,
    },
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ShowShareWords {
    Instruction,
    ShareWords,
    Confirm,
    CheckBackupIntro,
    CheckBackupMenu,
}

impl FlowController for ShowShareWords {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, _direction: Direction) -> Decision {
        self.do_nothing()
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
            (Self::CheckBackupIntro, FlowMsg::Info) => Self::CheckBackupMenu.goto(),
            (Self::CheckBackupMenu, FlowMsg::Choice(0)) => self.return_msg(FlowMsg::Cancelled),
            (Self::CheckBackupMenu, FlowMsg::Cancelled) => Self::CheckBackupIntro.goto(),
            _ => self.do_nothing(),
        }
    }
}

pub fn new_show_share_words_flow(
    words: Vec<TString<'static>, 33>,
    subtitle: TString<'static>,
    instructions_paragraphs: Option<ParagraphVecShort<'static>>,
    instructions_verb: Option<TString<'static>>,
    text_confirm: TString<'static>,
    text_check: TString<'static>,
) -> Result<SwipeFlow, error::Error> {
    let br: ButtonRequest = ButtonRequestCode::ResetDevice.with_name("share_words");
    // Determine whether to show the instructions or not
    let has_intro = instructions_paragraphs.is_some();
    let nwords = words.len();

    let instruction = TextScreen::new(
        instructions_paragraphs
            .unwrap_or_default()
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical().with_spacing(24)),
    )
    .with_header(Header::new(TR::reset__recovery_wallet_backup_title.into()))
    .with_action_bar(ActionBar::new_single(Button::with_text(
        instructions_verb.unwrap_or(TR::buttons__continue.into()),
    )))
    .with_page_limit(1)
    .map(|msg| match msg {
        TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
        TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
        _ => Some(FlowMsg::Cancelled),
    });

    let share_words = ShareWordsScreen::new(words, has_intro)
        .with_subtitle(subtitle)
        .map(|msg| match msg {
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

    let check_backup_paragraphs = Paragraph::new(&theme::TEXT_REGULAR, text_check)
        .into_paragraphs()
        .with_placement(LinearPlacement::vertical());

    let check_backup_intro = TextScreen::new(check_backup_paragraphs)
        .with_header(Header::new(TR::reset__check_wallet_backup_title.into()).with_menu_button())
        .with_action_bar(ActionBar::new_single(Button::with_text(
            TR::buttons__continue.into(),
        )))
        .map(|msg| match msg {
            TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
            TextScreenMsg::Menu => Some(FlowMsg::Info),
            _ => None,
        });
    let check_backup_menu = VerticalMenuScreen::new(
        VerticalMenu::<ShortMenuVec>::empty().with_item(Button::new_menu_item(
            TR::backup__title_skip.into(),
            theme::menu_item_title_orange(),
        )),
    )
    .with_header(Header::new(TR::reset__check_wallet_backup_title.into()).with_close_button())
    .map(|msg| match msg {
        VerticalMenuScreenMsg::Selected(i) => Some(FlowMsg::Choice(i)),
        VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
        _ => None,
    });
    let mut res = if has_intro {
        SwipeFlow::new(&ShowShareWords::Instruction)?
    } else {
        SwipeFlow::new(&ShowShareWords::ShareWords)?
    };
    if has_intro {
        res.add_page(
            &ShowShareWords::Instruction,
            instruction
                .one_button_request(br)
                .with_pages(move |_| nwords + 2),
        )?
        .add_page(&ShowShareWords::ShareWords, share_words)?
    } else {
        // If there is no introduction page, share words page sends the BR instead
        // the instruction page is just a placeholder
        res.add_page(&ShowShareWords::Instruction, instruction)?
            .add_page(
                &ShowShareWords::ShareWords,
                share_words
                    .one_button_request(br)
                    .with_pages(move |_| nwords + 1),
            )?
    };

    res.add_page(&ShowShareWords::Confirm, confirm)?
        .add_page(&ShowShareWords::CheckBackupIntro, check_backup_intro)?
        .add_page(&ShowShareWords::CheckBackupMenu, check_backup_menu)?;
    Ok(res)
}
