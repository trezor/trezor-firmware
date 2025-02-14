use crate::{
    error,
    strutil::TString,
    translations::TR,
    ui::{
        component::{text::op::OpTextLayout, ComponentExt, FormattedText},
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::Direction,
        layout_eckhart::{
            component::{
                ActionBar, Button, Header, ShareWordsScreen, ShareWordsScreenMsg, TextScreen,
                TextScreenMsg,
            },
            fonts, theme,
        },
    },
};

use heapless::Vec;

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ShowShareWords {
    ShareWords,
    Confirm,
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
            (Self::ShareWords, FlowMsg::Cancelled) => self.return_msg(FlowMsg::Cancelled),
            (Self::ShareWords, FlowMsg::Confirmed) => Self::Confirm.goto(),
            (Self::Confirm, FlowMsg::Cancelled) => Self::ShareWords.goto(),
            (Self::Confirm, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            _ => self.do_nothing(),
        }
    }
}

pub fn new_show_share_words_flow(
    words: Vec<TString<'static>, 33>,
    text_confirm: TString<'static>,
) -> Result<SwipeFlow, error::Error> {
    let share_words = ShareWordsScreen::new(words).map(|msg| match msg {
        ShareWordsScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
        ShareWordsScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
        ShareWordsScreenMsg::Menu => todo!(),
    });

    let op_confirm =
        OpTextLayout::new(theme::TEXT_NORMAL).text(text_confirm, fonts::FONT_SATOSHI_REGULAR_38);

    let confirm = TextScreen::new(FormattedText::new(op_confirm))
        .with_header(Header::new(TR::reset__recovery_wallet_backup_title.into()).with_menu_button())
        .with_action_bar(ActionBar::new_double(
            Button::with_icon(theme::ICON_CHEVRON_LEFT),
            Button::with_text(TR::buttons__hold_to_confirm.into())
                .with_long_press(theme::CONFIRM_HOLD_DURATION),
        ))
        .map(|msg| match msg {
            TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
            TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
            TextScreenMsg::Menu => todo!(),
        });

    let res = SwipeFlow::new(&ShowShareWords::ShareWords)?
        .with_page(&ShowShareWords::ShareWords, share_words)?
        .with_page(&ShowShareWords::Confirm, confirm)?;
    Ok(res)
}
