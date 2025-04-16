use crate::{
    error,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            text::paragraphs::{Paragraph, ParagraphSource, Paragraphs},
            ComponentExt,
        },
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::{Alignment, Direction, LinearPlacement, Offset},
    },
};

use super::super::{
    component::Button,
    firmware::{
        ActionBar, Header, HeaderMsg, Hint, TextScreen, TextScreenMsg, VerticalMenu,
        VerticalMenuScreen, VerticalMenuScreenMsg,
    },
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum PromptBackup {
    Intro,
    Menu,
    SkipBackup,
}

impl FlowController for PromptBackup {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, _direction: Direction) -> Decision {
        self.do_nothing()
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Intro, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Intro, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            (Self::Menu, FlowMsg::Choice(0)) => Self::SkipBackup.swipe_left(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Intro.goto(),
            (Self::SkipBackup, FlowMsg::Cancelled) => Self::Intro.goto(),
            (Self::SkipBackup, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Cancelled),
            _ => self.do_nothing(),
        }
    }
}

pub fn new_prompt_backup() -> Result<SwipeFlow, error::Error> {
    let title: TString = TR::backup__title_create_wallet_backup.into();
    let content: TString = TR::backup__it_should_be_backed_up.into();

    let paragraphs = Paragraphs::new(Paragraph::new(&theme::TEXT_REGULAR, content))
        .with_placement(LinearPlacement::vertical());

    let content_intro = TextScreen::new(paragraphs)
        .with_header(Header::new(title).with_menu_button())
        .with_action_bar(ActionBar::new_single(Button::with_text(
            TR::buttons__continue.into(),
        )))
        .map(|msg| match msg {
            TextScreenMsg::Menu => Some(FlowMsg::Info),
            TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
            _ => None,
        });

    let content_menu = VerticalMenuScreen::new(
        VerticalMenu::empty().item(
            Button::with_text(TR::backup__title_skip.into())
                .styled(theme::menu_item_title_orange())
                .with_text_align(Alignment::Start)
                .with_content_offset(Offset::x(12)),
        ),
    )
    .with_header(
        Header::new(title)
            .with_right_button(Button::with_icon(theme::ICON_CROSS), HeaderMsg::Cancelled),
    )
    .map(|msg| match msg {
        VerticalMenuScreenMsg::Selected(i) => Some(FlowMsg::Choice(i)),
        VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
        _ => None,
    });

    let paragraphs_skip_intro = Paragraph::new(
        &theme::TEXT_REGULAR,
        TR::backup__create_backup_to_prevent_loss,
    )
    .into_paragraphs()
    .with_placement(LinearPlacement::vertical());

    let content_skip_intro = TextScreen::new(paragraphs_skip_intro)
        .with_header(
            Header::new(TR::words__important.into())
                .with_icon(theme::ICON_WARNING, theme::ORANGE)
                .with_text_style(theme::label_title_danger()),
        )
        .with_action_bar(ActionBar::new_double(
            Button::with_icon(theme::ICON_CHEVRON_LEFT),
            Button::with_text(TR::buttons__skip.into()).styled(theme::button_cancel()),
        ))
        .with_hint(Hint::new_instruction(TR::backup__not_recommend, None))
        .map(|msg| match msg {
            TextScreenMsg::Menu => Some(FlowMsg::Cancelled),
            TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
            TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
        });

    let mut res = SwipeFlow::new(&PromptBackup::Intro)?;
    res.add_page(&PromptBackup::Intro, content_intro)?
        .add_page(&PromptBackup::Menu, content_menu)?
        .add_page(&PromptBackup::SkipBackup, content_skip_intro)?;
    Ok(res)
}
