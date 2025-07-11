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
        geometry::{Direction, LinearPlacement},
    },
};

use super::super::{
    component::Button,
    firmware::{
        ActionBar, Header, HeaderMsg, Hint, ShortMenuVec, TextScreen, TextScreenMsg, VerticalMenu,
        VerticalMenuScreen, VerticalMenuScreenMsg,
    },
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ShowTutorial {
    StepWelcome,
    StepBegin,
    StepNavigation,
    StepMenu,
    Menu,
    StepHold,
    Tropic,
    HoldToExit,
    StepDone,
}

impl FlowController for ShowTutorial {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, _direction: Direction) -> Decision {
        self.do_nothing()
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::StepWelcome, FlowMsg::Confirmed) => Self::StepBegin.goto(),
            (Self::StepBegin, FlowMsg::Confirmed) => Self::StepNavigation.goto(),
            (Self::StepNavigation, FlowMsg::Confirmed) => Self::StepMenu.goto(),
            (Self::StepNavigation, FlowMsg::Cancelled) => Self::StepBegin.goto(),
            (Self::StepMenu, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Choice(0)) => Self::StepHold.goto(),
            (Self::Menu, FlowMsg::Choice(1)) => Self::Tropic.goto(),
            (Self::Menu, FlowMsg::Choice(2)) => Self::StepBegin.goto(),
            (Self::Menu, FlowMsg::Choice(3)) => Self::HoldToExit.goto(),
            (Self::Menu, FlowMsg::Cancelled) => Self::StepMenu.goto(),
            (Self::Tropic, FlowMsg::Cancelled) => Self::Menu.goto(),
            (Self::StepHold, FlowMsg::Confirmed) => Self::StepDone.goto(),
            (Self::HoldToExit, FlowMsg::Confirmed) => Self::StepDone.goto(),
            (Self::StepDone, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            _ => self.do_nothing(),
        }
    }
}

pub fn new_show_tutorial() -> Result<SwipeFlow, error::Error> {
    let content_step_welcome = TextScreen::new(
        Paragraph::new(&theme::TEXT_REGULAR, TR::tutorial__welcome_safe7)
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical()),
    )
    .with_action_bar(ActionBar::new_timeout(
        Button::with_text("TROPIC01".into()),
        3000,
    ))
    .map(|msg| match msg {
        TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
        _ => None,
    });

    let content_step_begin = TextScreen::new(
        Paragraph::new(&theme::TEXT_REGULAR, TR::tutorial__welcome_safe7)
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical()),
    )
    .with_action_bar(ActionBar::new_single(Button::with_text(
        TR::instructions__tap_to_start.into(),
    )))
    .map(|msg| match msg {
        TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
        _ => None,
    });

    let navigation_paragraphs = Paragraphs::new([
        Paragraph::new(
            &theme::TEXT_REGULAR,
            "Use buttons at the bottom to navigate and confirm your actions.",
        ),
        Paragraph::new(&theme::TEXT_REGULAR, "Everything at your fingertips."),
    ])
    .with_placement(LinearPlacement::vertical())
    .with_spacing(24);
    let content_step_navigation = TextScreen::new(navigation_paragraphs)
        .with_action_bar(ActionBar::new_double(
            Button::with_icon(theme::ICON_CHEVRON_UP),
            Button::with_text(TR::buttons__continue.into()),
        ))
        .map(|msg| match msg {
            TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
            TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
            _ => None,
        });

    let step_menu_paragraphs = Paragraphs::new([
        Paragraph::new(
            &theme::TEXT_REGULAR,
            "Find context-specific actions and options in the menu.",
        ),
        Paragraph::new(
            &theme::TEXT_REGULAR,
            "View more info, quit flow, you got it.",
        ),
    ])
    .with_placement(LinearPlacement::vertical())
    .with_spacing(24);
    let content_step_menu = TextScreen::new(step_menu_paragraphs)
        .with_header(Header::new("Handy Menu".into()).with_right_button(
            Button::with_icon(theme::ICON_MENU).styled(theme::button_menu_tutorial()),
            HeaderMsg::Menu,
        ))
        .with_action_bar(ActionBar::new_text_only(
            TR::instructions__menu_to_continue.into(),
        ))
        .map(|msg| match msg {
            TextScreenMsg::Menu => Some(FlowMsg::Info),
            _ => None,
        });

    let menu = VerticalMenu::<ShortMenuVec>::empty()
        .with_item(Button::new_menu_item_with_subtext(
            "Continue tutorial".into(),
            theme::menu_item_title(),
            "One more step".into(),
            None,
        ))
        .with_item(Button::new_menu_item(
            "What is TROPIC01?".into(),
            theme::menu_item_title(),
        ))
        .with_item(Button::new_menu_item(
            "Restart tutorial".into(),
            theme::menu_item_title(),
        ))
        .with_item(Button::new_menu_item(
            "Exit tutorial".into(),
            theme::menu_item_title_orange(),
        ));
    let content_menu = VerticalMenuScreen::new(menu)
        .with_header(Header::new(TString::empty()).with_close_button())
        .map(|msg| match msg {
            VerticalMenuScreenMsg::Selected(i) => Some(FlowMsg::Choice(i)),
            VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
            _ => None,
        });

    let content_step_hold = TextScreen::new(
        Paragraph::new(
            &theme::TEXT_REGULAR,
            "Hold a button to confirm important actions.",
        )
        .into_paragraphs()
        .with_placement(LinearPlacement::vertical()),
    )
    .with_header(Header::new("last one".into()))
    .with_hint(Hint::new_instruction(
        "You can replay this tutorial from the Trezor Suite app.",
        Some(theme::ICON_INFO),
    ))
    .with_action_bar(ActionBar::new_single(
        Button::with_text("Hold to exit tutorial".into())
            .with_long_press(theme::CONFIRM_HOLD_DURATION)
            .styled(theme::button_confirm()),
    ))
    .map(|msg| match msg {
        TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
        _ => None,
    });

    let content_tropic = TextScreen::new(
        Paragraph::new(
            &theme::TEXT_REGULAR,
            "TROPIC01 is a revolutionary secure element designed to deliver tamper-proof next-gen protection with an open",
        )
        .into_paragraphs()
        .with_placement(LinearPlacement::vertical()),
    )
    .with_header(Header::new("What is Tropic01?".into()).with_close_button()).map(|msg| match msg {
        TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
        _ => None,
    });

    let content_hold_to_exit = TextScreen::new(
        Paragraph::new(
            &theme::TEXT_REGULAR,
            "Hold a button to confirm important actions.",
        )
        .into_paragraphs()
        .with_placement(LinearPlacement::vertical()),
    )
    .with_header(Header::new("last one".into()))
    .with_hint(Hint::new_instruction(
        "You can replay this tutorial from the Trezor Suite app.",
        Some(theme::ICON_INFO),
    ))
    .with_action_bar(ActionBar::new_single(
        Button::with_text("Hold to exit tutorial".into())
            .with_long_press(theme::CONFIRM_HOLD_DURATION)
            .with_long_press_danger(true)
            .styled(theme::button_actionbar_danger()),
    ))
    .map(|msg| match msg {
        TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
        _ => None,
    });

    let content_step_done = TextScreen::new(
        Paragraph::new(
            &theme::TEXT_REGULAR,
            "You're all set to start using your device!",
        )
        .into_paragraphs()
        .with_placement(LinearPlacement::vertical()),
    )
    .with_header(
        Header::new("Well done".into())
            .with_icon(theme::ICON_DONE, theme::GREEN_LIGHT)
            .with_text_style(theme::label_title_confirm()),
    )
    .with_action_bar(ActionBar::new_single(Button::with_text("Finish".into())))
    .map(|msg| match msg {
        TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
        _ => None,
    });

    let mut res = SwipeFlow::new(&ShowTutorial::StepWelcome)?;
    res.add_page(&ShowTutorial::StepWelcome, content_step_welcome)?
        .add_page(&ShowTutorial::StepBegin, content_step_begin)?
        .add_page(&ShowTutorial::StepNavigation, content_step_navigation)?
        .add_page(&ShowTutorial::StepMenu, content_step_menu)?
        .add_page(&ShowTutorial::Menu, content_menu)?
        .add_page(&ShowTutorial::StepHold, content_step_hold)?
        .add_page(&ShowTutorial::Tropic, content_tropic)?
        .add_page(&ShowTutorial::HoldToExit, content_hold_to_exit)?
        .add_page(&ShowTutorial::StepDone, content_step_done)?;
    Ok(res)
}
