use crate::{
    error,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            swipe_detect::SwipeSettings,
            text::paragraphs::{Paragraph, Paragraphs},
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
pub enum ConfirmFirmwareUpdate {
    Intro,
    Menu,
    Fingerprint,
    Confirm,
}

impl FlowController for ConfirmFirmwareUpdate {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Intro, Direction::Left) => Self::Menu.swipe(direction),
            (Self::Intro, Direction::Up) => Self::Confirm.swipe(direction),
            (Self::Menu, Direction::Right) => Self::Intro.swipe(direction),
            (Self::Fingerprint, Direction::Right) => Self::Menu.swipe(direction),
            (Self::Confirm, Direction::Down) => Self::Intro.swipe(direction),
            (Self::Confirm, Direction::Left) => Self::Menu.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Intro, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Intro.swipe_right(),
            (Self::Menu, FlowMsg::Choice(0)) => Self::Fingerprint.goto(),
            (Self::Menu, FlowMsg::Choice(1)) => self.return_msg(FlowMsg::Cancelled),
            (Self::Fingerprint, FlowMsg::Cancelled) => Self::Menu.goto(),
            (Self::Confirm, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            (Self::Confirm, FlowMsg::Info) => Self::Menu.goto(),
            _ => self.do_nothing(),
        }
    }
}

pub fn new_confirm_firmware_update(
    description: TString<'static>,
    fingerprint: TString<'static>,
) -> Result<SwipeFlow, error::Error> {
    let paragraphs = Paragraphs::new(Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, description));
    let content_intro = Frame::left_aligned(
        TR::firmware_update__title.into(),
        SwipeContent::new(paragraphs),
    )
    .with_menu_button()
    .with_swipeup_footer(None)
    .with_swipe(Direction::Left, SwipeSettings::default())
    .map_to_button_msg();

    let content_menu = Frame::left_aligned(
        TString::empty(),
        VerticalMenu::empty()
            .item(
                theme::ICON_CHEVRON_RIGHT,
                TR::firmware_update__title_fingerprint.into(),
            )
            .danger(theme::ICON_CANCEL, TR::buttons__cancel.into()),
    )
    .with_cancel_button()
    .with_swipe(Direction::Right, SwipeSettings::immediate())
    .map(super::util::map_to_choice);

    let paragraphs_fingerprint =
        Paragraphs::new(Paragraph::new(&theme::TEXT_MONO_GREY_LIGHT, fingerprint));
    let content_fingerprint = Frame::left_aligned(
        TR::firmware_update__title_fingerprint.into(),
        SwipeContent::new(paragraphs_fingerprint),
    )
    .with_cancel_button()
    .with_swipe(Direction::Right, SwipeSettings::default())
    .map_to_button_msg();

    let content_confirm = Frame::left_aligned(
        TR::firmware_update__title.into(),
        SwipeContent::new(PromptScreen::new_hold_to_confirm()),
    )
    .with_menu_button()
    .with_footer(TR::instructions__hold_to_confirm.into(), None)
    .with_swipe(Direction::Down, SwipeSettings::default())
    .with_swipe(Direction::Left, SwipeSettings::default())
    .map(super::util::map_to_confirm);

    let mut res = SwipeFlow::new(&ConfirmFirmwareUpdate::Intro)?;
    res.add_page(&ConfirmFirmwareUpdate::Intro, content_intro)?
        .add_page(&ConfirmFirmwareUpdate::Menu, content_menu)?
        .add_page(&ConfirmFirmwareUpdate::Fingerprint, content_fingerprint)?
        .add_page(&ConfirmFirmwareUpdate::Confirm, content_confirm)?;
    Ok(res)
}
