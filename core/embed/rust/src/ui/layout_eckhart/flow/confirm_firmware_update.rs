use super::super::component::Button;
use super::super::firmware::{
    ActionBar, Header, Hint, ShortMenuVec, TextScreen, TextScreenMsg, VerticalMenu,
    VerticalMenuScreen, VerticalMenuScreenMsg,
};
use super::super::theme;
use crate::error;
use crate::strutil::TString;
use crate::translations::TR;
use crate::ui::component::text::paragraphs::{Paragraph, ParagraphSource};
use crate::ui::component::ComponentExt;
use crate::ui::flow::base::{Decision, DecisionBuilder as _};
use crate::ui::flow::{FlowController, FlowMsg, SwipeFlow};
use crate::ui::geometry::{Direction, LinearPlacement};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmFirmwareUpdate {
    Intro,
    Menu,
    Fingerprint,
}

impl FlowController for ConfirmFirmwareUpdate {
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
            (Self::Menu, FlowMsg::Cancelled) => Self::Intro.goto(),
            (Self::Menu, FlowMsg::Choice(0)) => Self::Fingerprint.goto(),
            (Self::Menu, FlowMsg::Choice(1)) => self.return_msg(FlowMsg::Cancelled),
            (Self::Fingerprint, FlowMsg::Cancelled) => Self::Menu.goto(),
            (Self::Intro, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            _ => self.do_nothing(),
        }
    }
}

pub fn new_confirm_firmware_update(
    description: TString<'static>,
    fingerprint: TString<'static>,
) -> Result<SwipeFlow, error::Error> {
    let title = TR::firmware_update__title.into();
    let intro_paragraphs = Paragraph::new(&theme::firmware::TEXT_REGULAR, description)
        .into_paragraphs()
        .with_placement(LinearPlacement::vertical());
    let content_intro = TextScreen::new(intro_paragraphs)
        .with_header(Header::new(title).with_menu_button())
        .with_hint(Hint::new_instruction(
            TR::firmware_update__restart,
            Some(theme::ICON_INFO),
        ))
        .with_action_bar(ActionBar::new_single(Button::with_text(
            TR::buttons__confirm.into(),
        )))
        .map(|msg| match msg {
            TextScreenMsg::Menu => Some(FlowMsg::Info),
            TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
            _ => None,
        });

    let menu = VerticalMenu::<ShortMenuVec>::empty()
        .with_item(Button::new_menu_item(
            TR::firmware_update__title_fingerprint.into(),
            theme::firmware::menu_item_title(),
        ))
        .with_item(Button::new_cancel_menu_item(TR::buttons__cancel.into()));

    let content_menu = VerticalMenuScreen::new(menu)
        .with_header(Header::new(title).with_close_button())
        .map(|msg| match msg {
            VerticalMenuScreenMsg::Selected(idx) => Some(FlowMsg::Choice(idx)),
            VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
            _ => None,
        });

    let fingerprint_paragraphs = Paragraph::new(&theme::firmware::TEXT_MONO_LIGHT, fingerprint)
        .into_paragraphs()
        .with_placement(LinearPlacement::vertical());
    let content_fingerprint = TextScreen::new(fingerprint_paragraphs)
        .with_header(Header::new(TR::firmware_update__title_fingerprint.into()).with_close_button())
        .map(|msg| match msg {
            TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
            _ => None,
        });

    let mut res = SwipeFlow::new(&ConfirmFirmwareUpdate::Intro)?;
    res.add_page(&ConfirmFirmwareUpdate::Intro, content_intro)?
        .add_page(&ConfirmFirmwareUpdate::Menu, content_menu)?
        .add_page(&ConfirmFirmwareUpdate::Fingerprint, content_fingerprint)?;
    Ok(res)
}
