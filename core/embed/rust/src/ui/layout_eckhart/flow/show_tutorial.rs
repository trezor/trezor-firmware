use crate::{
    error,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            text::paragraphs::{Paragraph, ParagraphSource, Paragraphs},
            ComponentExt, MsgMap,
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
        ActionBar, Header, HeaderMsg, Hint, ShortMenuVec, TextScreen, TextScreenMsg,
        TutorialWelcomeScreen, TutorialWelcomeScreenMsg, VerticalMenu, VerticalMenuScreen,
        VerticalMenuScreenMsg,
    },
    theme::{self, Gradient},
};

const WELCOME_SCREEN_DURATION_MS: u32 = 3000;
type TropicScreen = TextScreen<Paragraphs<[Paragraph<'static>; 3]>>;
type TropicScreenMap = MsgMap<TropicScreen, fn(TextScreenMsg) -> Option<FlowMsg>>;

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ShowTutorial {
    StepWelcome,
    StepBegin,
    StepNavigation,
    StepMenu,
    Menu,
    MenuTropic,
    StepHold,
    StepHoldMenu,
    StepHoldMenuTropic,
    HoldToExit,
    HoldToExitMenu,
    HoldToExitMenuTropic,
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
            (Self::Menu, FlowMsg::Choice(1)) => Self::MenuTropic.goto(),
            (Self::Menu, FlowMsg::Choice(2)) => Self::StepBegin.goto(),
            (Self::Menu, FlowMsg::Choice(3)) => Self::HoldToExit.goto(),
            (Self::Menu, FlowMsg::Cancelled) => Self::StepMenu.goto(),
            (Self::MenuTropic, FlowMsg::Cancelled) => Self::Menu.goto(),
            (Self::StepHold, FlowMsg::Confirmed) => Self::StepDone.goto(),
            (Self::StepHold, FlowMsg::Info) => Self::StepHoldMenu.goto(),
            (Self::StepHoldMenu, FlowMsg::Choice(0)) => Self::StepHoldMenuTropic.goto(),
            (Self::StepHoldMenu, FlowMsg::Choice(1)) => Self::StepBegin.goto(),
            (Self::StepHoldMenu, FlowMsg::Choice(2)) => Self::HoldToExit.goto(),
            (Self::StepHoldMenu, FlowMsg::Cancelled) => Self::StepHold.goto(),
            (Self::StepHoldMenuTropic, FlowMsg::Cancelled) => Self::StepHoldMenu.goto(),
            (Self::HoldToExit, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Cancelled),
            (Self::HoldToExit, FlowMsg::Info) => Self::HoldToExitMenu.goto(),
            (Self::HoldToExitMenu, FlowMsg::Choice(0)) => Self::HoldToExitMenuTropic.goto(),
            (Self::HoldToExitMenu, FlowMsg::Choice(1)) => Self::StepBegin.goto(),
            (Self::HoldToExitMenu, FlowMsg::Cancelled) => Self::HoldToExit.goto(),
            (Self::HoldToExitMenuTropic, FlowMsg::Cancelled) => Self::HoldToExitMenu.goto(),
            (Self::StepDone, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            _ => self.do_nothing(),
        }
    }
}

fn content_tropic() -> TropicScreenMap {
    TextScreen::new(
        Paragraphs::new([
            Paragraph::new(&theme::TEXT_REGULAR, TR::tutorial__tropic_info1).break_after(),
            Paragraph::new(&theme::TEXT_REGULAR, TR::tutorial__tropic_info2).break_after(),
            Paragraph::new(&theme::TEXT_REGULAR, TR::tutorial__tropic_info3),
        ])
        .with_placement(LinearPlacement::vertical()),
    )
    .with_header(Header::new(TR::tutorial__what_is_tropic.into()).with_close_button())
    .map(|msg| match msg {
        TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
        _ => None,
    })
}

pub fn new_show_tutorial() -> Result<SwipeFlow, error::Error> {
    let content_step_welcome = TutorialWelcomeScreen::new().map(|msg| match msg {
        TutorialWelcomeScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
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

    let navigation_paragraphs = Paragraph::new(&theme::TEXT_REGULAR, TR::tutorial__navigation_ts7)
        .into_paragraphs()
        .with_placement(LinearPlacement::vertical())
        .with_spacing(theme::TEXT_VERTICAL_SPACING);
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
        Paragraph::new(&theme::TEXT_REGULAR, TR::tutorial__menu),
        Paragraph::new(&theme::TEXT_REGULAR, TR::tutorial__menu_appendix),
    ])
    .with_placement(LinearPlacement::vertical())
    .with_spacing(theme::TEXT_VERTICAL_SPACING);
    let content_step_menu = TextScreen::new(step_menu_paragraphs)
        .with_header(
            Header::new(TR::tutorial__title_handy_menu.into()).with_right_button(
                Button::with_icon(theme::ICON_MENU).styled(theme::button_menu_tutorial()),
                HeaderMsg::Menu,
            ),
        )
        .with_action_bar(ActionBar::new_text_only(
            TR::instructions__menu_to_continue.into(),
        ))
        .map(|msg| match msg {
            TextScreenMsg::Menu => Some(FlowMsg::Info),
            _ => None,
        });

    let menu = VerticalMenu::<ShortMenuVec>::empty()
        .with_item(Button::new_menu_item_with_subtext(
            TR::tutorial__continue.into(),
            theme::menu_item_title(),
            TR::tutorial__one_more_step.into(),
            &theme::TEXT_MENU_ITEM_SUBTITLE,
        ))
        .with_item(Button::new_menu_item(
            TR::tutorial__what_is_tropic.into(),
            theme::menu_item_title(),
        ))
        .with_item(Button::new_menu_item(
            TR::tutorial__restart_tutorial.into(),
            theme::menu_item_title(),
        ))
        .with_item(Button::new_menu_item(
            TR::tutorial__exit.into(),
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
        Paragraph::new(&theme::TEXT_REGULAR, TR::tutorial__title_hold)
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical()),
    )
    .with_header(Header::new(TR::tutorial__last_one.into()).with_menu_button())
    .with_hint(Hint::new_instruction(
        TR::tutorial__suite_restart,
        Some(theme::ICON_INFO),
    ))
    .with_action_bar(ActionBar::new_single(
        Button::with_text(TR::instructions__hold_to_exit_tutorial.into())
            .with_long_press(theme::CONFIRM_HOLD_DURATION)
            .styled(theme::button_confirm())
            .with_gradient(Gradient::SignGreen),
    ))
    .map(|msg| match msg {
        TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
        TextScreenMsg::Menu => Some(FlowMsg::Info),
        _ => None,
    });

    let step_hold_menu = VerticalMenu::<ShortMenuVec>::empty()
        .with_item(Button::new_menu_item(
            TR::tutorial__what_is_tropic.into(),
            theme::menu_item_title(),
        ))
        .with_item(Button::new_menu_item(
            TR::tutorial__restart_tutorial.into(),
            theme::menu_item_title(),
        ))
        .with_item(Button::new_menu_item(
            TR::tutorial__exit.into(),
            theme::menu_item_title_orange(),
        ));
    let content_step_hold_menu = VerticalMenuScreen::new(step_hold_menu)
        .with_header(Header::new(TString::empty()).with_close_button())
        .map(|msg| match msg {
            VerticalMenuScreenMsg::Selected(i) => Some(FlowMsg::Choice(i)),
            VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
            _ => None,
        });

    let content_hold_to_exit = TextScreen::new(
        Paragraph::new(&theme::TEXT_REGULAR, TR::tutorial__title_hold)
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical()),
    )
    .with_header(Header::new(TR::tutorial__last_one.into()).with_menu_button())
    .with_hint(Hint::new_instruction(
        TR::tutorial__suite_restart,
        Some(theme::ICON_INFO),
    ))
    .with_action_bar(ActionBar::new_single(
        Button::with_text(TR::instructions__hold_to_exit_tutorial.into())
            .with_long_press(theme::CONFIRM_HOLD_DURATION)
            .with_long_press_danger(true)
            .styled(theme::button_actionbar_danger())
            .with_gradient(Gradient::Alert),
    ))
    .map(|msg| match msg {
        TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
        TextScreenMsg::Menu => Some(FlowMsg::Info),
        _ => None,
    });

    let hold_to_exit_menu = VerticalMenu::<ShortMenuVec>::empty()
        .with_item(Button::new_menu_item(
            TR::tutorial__what_is_tropic.into(),
            theme::menu_item_title(),
        ))
        .with_item(Button::new_menu_item(
            TR::tutorial__restart_tutorial.into(),
            theme::menu_item_title(),
        ));
    let content_hold_to_exit_menu = VerticalMenuScreen::new(hold_to_exit_menu)
        .with_header(Header::new(TString::empty()).with_close_button())
        .map(|msg| match msg {
            VerticalMenuScreenMsg::Selected(i) => Some(FlowMsg::Choice(i)),
            VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
            _ => None,
        });

    let content_step_done = TextScreen::new(
        Paragraph::new(&theme::TEXT_REGULAR, TR::tutorial__ready_to_use_safe5)
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical()),
    )
    .with_header(
        Header::new(TR::tutorial__title_well_done.into())
            .with_icon(theme::ICON_DONE, theme::GREEN_LIGHT)
            .with_text_style(theme::label_title_confirm()),
    )
    .with_action_bar(ActionBar::new_single(Button::with_text(
        TR::buttons__finish.into(),
    )))
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
        .add_page(&ShowTutorial::MenuTropic, content_tropic())?
        .add_page(&ShowTutorial::StepHold, content_step_hold)?
        .add_page(&ShowTutorial::StepHoldMenu, content_step_hold_menu)?
        .add_page(&ShowTutorial::StepHoldMenuTropic, content_tropic())?
        .add_page(&ShowTutorial::HoldToExit, content_hold_to_exit)?
        .add_page(&ShowTutorial::HoldToExitMenu, content_hold_to_exit_menu)?
        .add_page(&ShowTutorial::HoldToExitMenuTropic, content_tropic())?
        .add_page(&ShowTutorial::StepDone, content_step_done)?;
    Ok(res)
}
