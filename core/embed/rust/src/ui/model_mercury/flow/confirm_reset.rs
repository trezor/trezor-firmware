use crate::{
    error,
    strutil::TString,
    translations::TR,
    ui::{
        button_request::ButtonRequestCode,
        component::{
            swipe_detect::SwipeSettings,
            text::paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort},
            ButtonRequestExt, ComponentExt,
        },
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::Direction,
    },
};

use super::super::{
    component::{
        Frame, FrameMsg, PromptMsg, PromptScreen, SwipeContent, VerticalMenu, VerticalMenuChoiceMsg,
    },
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmResetCreate {
    Intro,
    Menu,
    Confirm,
}

impl FlowController for ConfirmResetCreate {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Intro, Direction::Left) => Self::Menu.swipe(direction),
            (Self::Intro, Direction::Up) => Self::Confirm.swipe(direction),
            (Self::Menu, Direction::Right) => Self::Intro.swipe(direction),
            (Self::Confirm, Direction::Down) => Self::Intro.swipe(direction),
            (Self::Confirm, Direction::Left) => Self::Menu.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Intro, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Intro.swipe_right(),
            (Self::Menu, FlowMsg::Choice(0)) => self.return_msg(FlowMsg::Cancelled),
            (Self::Confirm, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            (Self::Confirm, FlowMsg::Info) => Self::Menu.goto(),
            _ => self.do_nothing(),
        }
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmResetRecover {
    Intro,
    Menu,
}

impl FlowController for ConfirmResetRecover {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Intro, Direction::Left) => Self::Menu.swipe(direction),
            (Self::Menu, Direction::Right) => Self::Intro.swipe(direction),
            (Self::Intro, Direction::Up) => self.return_msg(FlowMsg::Confirmed),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Intro, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Intro.swipe_right(),
            (Self::Menu, FlowMsg::Choice(0)) => self.return_msg(FlowMsg::Cancelled),
            _ => self.do_nothing(),
        }
    }
}

pub fn new_confirm_reset(recovery: bool) -> Result<SwipeFlow, error::Error> {
    let (title, br, cancel_btn_text) = if recovery {
        (
            TR::recovery__title_recover.into(),
            ButtonRequestCode::ProtectCall.with_name("recover_device"),
            TR::recovery__title_cancel_recovery.into(),
        )
    } else {
        (
            TR::reset__title_create_wallet.into(),
            ButtonRequestCode::ResetDevice.with_name("setup_device"),
            TR::reset__cancel_create_wallet.into(),
        )
    };

    let paragraphs = ParagraphVecShort::from_iter([
        Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, TR::reset__by_continuing)
            .with_bottom_padding(17),
        Paragraph::new(&theme::TEXT_SUB_GREY, TR::reset__more_info_at),
        Paragraph::new(&theme::TEXT_SUB_GREY_LIGHT, TR::reset__tos_link),
    ])
    .into_paragraphs();
    let content_intro = Frame::left_aligned(title, SwipeContent::new(paragraphs))
        .with_menu_button()
        .with_footer(TR::instructions__swipe_up.into(), None)
        .with_swipe(Direction::Up, SwipeSettings::default())
        .with_swipe(Direction::Left, SwipeSettings::default())
        .map(|msg| matches!(msg, FrameMsg::Button(_)).then_some(FlowMsg::Info))
        .one_button_request(br);

    let content_menu = Frame::left_aligned(
        TString::empty(),
        VerticalMenu::empty().danger(theme::ICON_CANCEL, cancel_btn_text),
    )
    .with_cancel_button()
    .with_swipe(Direction::Right, SwipeSettings::immediate())
    .map(|msg| match msg {
        FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
        FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
    });

    let res = if recovery {
        SwipeFlow::new(&ConfirmResetRecover::Intro)?
            .with_page(&ConfirmResetRecover::Intro, content_intro)?
            .with_page(&ConfirmResetRecover::Menu, content_menu)?
    } else {
        let content_confirm = Frame::left_aligned(
            TR::reset__title_create_wallet.into(),
            SwipeContent::new(PromptScreen::new_hold_to_confirm()),
        )
        .with_menu_button()
        .with_footer(TR::instructions__hold_to_confirm.into(), None)
        .with_swipe(Direction::Down, SwipeSettings::default())
        .with_swipe(Direction::Left, SwipeSettings::default())
        .map(|msg| match msg {
            FrameMsg::Content(PromptMsg::Confirmed) => Some(FlowMsg::Confirmed),
            FrameMsg::Button(_) => Some(FlowMsg::Info),
            _ => None,
        })
        .one_button_request(ButtonRequestCode::ResetDevice.with_name("confirm_setup_device"));

        SwipeFlow::new(&ConfirmResetCreate::Intro)?
            .with_page(&ConfirmResetCreate::Intro, content_intro)?
            .with_page(&ConfirmResetCreate::Menu, content_menu)?
            .with_page(&ConfirmResetCreate::Confirm, content_confirm)?
    };
    Ok(res)
}
