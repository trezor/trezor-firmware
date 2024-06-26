use crate::{
    error,
    translations::TR,
    ui::{
        component::{
            swipe_detect::SwipeSettings,
            text::paragraphs::{Paragraph, Paragraphs},
            ComponentExt, SwipeDirection,
        },
        flow::{base::Decision, flow_store, FlowMsg, FlowState, FlowStore, SwipeFlow},
        layout::obj::LayoutObj,
        model_mercury::component::SwipeContent,
    },
};

use super::super::{
    component::{Frame, FrameMsg, PromptScreen, VerticalMenu, VerticalMenuChoiceMsg},
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq, ToPrimitive)]
pub enum ShowTutorial {
    StepWelcome,
    StepBegin,
    StepNavigation,
    StepMenu,
    StepHold,
    StepDone,
    Menu,
    DidYouKnow,
    HoldToExit,
}

impl FlowState for ShowTutorial {
    fn handle_swipe(&self, direction: SwipeDirection) -> Decision<Self> {
        match (self, direction) {
            (ShowTutorial::StepBegin, SwipeDirection::Up) => {
                Decision::Goto(ShowTutorial::StepNavigation, direction)
            }
            (ShowTutorial::StepNavigation, SwipeDirection::Up) => {
                Decision::Goto(ShowTutorial::StepMenu, direction)
            }
            (ShowTutorial::StepNavigation, SwipeDirection::Down) => {
                Decision::Goto(ShowTutorial::StepBegin, direction)
            }
            (ShowTutorial::StepMenu, SwipeDirection::Up) => {
                Decision::Goto(ShowTutorial::StepHold, direction)
            }
            (ShowTutorial::StepMenu, SwipeDirection::Down) => {
                Decision::Goto(ShowTutorial::StepNavigation, direction)
            }
            (ShowTutorial::StepMenu, SwipeDirection::Left) => {
                Decision::Goto(ShowTutorial::Menu, direction)
            }
            (ShowTutorial::Menu, SwipeDirection::Left) => {
                Decision::Goto(ShowTutorial::DidYouKnow, direction)
            }
            (ShowTutorial::Menu, SwipeDirection::Right) => {
                Decision::Goto(ShowTutorial::StepBegin, direction)
            }
            (ShowTutorial::DidYouKnow, SwipeDirection::Right) => {
                Decision::Goto(ShowTutorial::Menu, direction)
            }
            (ShowTutorial::StepDone, SwipeDirection::Up) => Decision::Return(FlowMsg::Confirmed),
            _ => Decision::Nothing,
        }
    }

    fn handle_event(&self, msg: FlowMsg) -> Decision<Self> {
        match (self, msg) {
            (ShowTutorial::StepWelcome, FlowMsg::Confirmed) => {
                Decision::Goto(ShowTutorial::StepBegin, SwipeDirection::Up)
            }
            (ShowTutorial::StepMenu, FlowMsg::Info) => {
                Decision::Goto(ShowTutorial::Menu, SwipeDirection::Left)
            }
            (ShowTutorial::Menu, FlowMsg::Choice(0)) => {
                Decision::Goto(ShowTutorial::DidYouKnow, SwipeDirection::Left)
            }
            (ShowTutorial::Menu, FlowMsg::Choice(1)) => {
                Decision::Goto(ShowTutorial::StepBegin, SwipeDirection::Right)
            }
            (ShowTutorial::Menu, FlowMsg::Choice(2)) => {
                Decision::Goto(ShowTutorial::HoldToExit, SwipeDirection::Up)
            }
            (ShowTutorial::Menu, FlowMsg::Cancelled) => {
                Decision::Goto(ShowTutorial::StepMenu, SwipeDirection::Right)
            }
            (ShowTutorial::DidYouKnow, FlowMsg::Cancelled) => {
                Decision::Goto(ShowTutorial::Menu, SwipeDirection::Right)
            }
            (ShowTutorial::StepHold, FlowMsg::Confirmed) => {
                Decision::Goto(ShowTutorial::StepDone, SwipeDirection::Up)
            }
            (ShowTutorial::HoldToExit, FlowMsg::Confirmed) => {
                Decision::Goto(ShowTutorial::StepDone, SwipeDirection::Up)
            }
            _ => Decision::Nothing,
        }
    }
}

use crate::micropython::{map::Map, obj::Obj, util};

#[allow(clippy::not_unsafe_ptr_arg_deref)]
pub extern "C" fn new_show_tutorial(_n_args: usize, _args: *const Obj, _kwargs: *mut Map) -> Obj {
    unsafe { util::try_or_raise(ShowTutorial::new_obj) }
}

impl ShowTutorial {
    fn new_obj() -> Result<Obj, error::Error> {
        let content_step_welcome = Frame::left_aligned(
            TR::tutorial__welcome_safe5.into(),
            SwipeContent::new(PromptScreen::new_tap_to_start()),
        )
        .with_footer(TR::instructions__tap_to_start.into(), None)
        .map(|msg| matches!(msg, FrameMsg::Content(())).then_some(FlowMsg::Confirmed));

        let content_step_begin = Frame::left_aligned(
            TR::tutorial__title_lets_begin.into(),
            SwipeContent::new(Paragraphs::new(Paragraph::new(
                &theme::TEXT_MAIN_GREY_LIGHT,
                TR::tutorial__lets_begin,
            ))),
        )
        .with_footer(
            TR::instructions__swipe_up.into(),
            Some(TR::tutorial__get_started.into()),
        )
        .with_swipe(SwipeDirection::Up, SwipeSettings::default())
        .map(|_| None);

        let content_step_navigation = Frame::left_aligned(
            TR::tutorial__title_easy_navigation.into(),
            SwipeContent::new(Paragraphs::new(Paragraph::new(
                &theme::TEXT_MAIN_GREY_LIGHT,
                TR::tutorial__swipe_up_and_down,
            ))),
        )
        .with_footer(
            TR::instructions__swipe_up.into(),
            Some(TR::tutorial__continue.into()),
        )
        .with_swipe(SwipeDirection::Up, SwipeSettings::default())
        .with_swipe(SwipeDirection::Down, SwipeSettings::default())
        .map(|_| None);

        let content_step_menu = Frame::left_aligned(
            TR::tutorial__title_handy_menu.into(),
            SwipeContent::new(Paragraphs::new(Paragraph::new(
                &theme::TEXT_MAIN_GREY_LIGHT,
                TR::tutorial__menu,
            ))),
        )
        .with_menu_button()
        .button_styled(theme::button_warning_low())
        .with_footer(
            TR::instructions__swipe_up.into(),
            Some(TR::buttons__continue.into()),
        )
        .with_swipe(SwipeDirection::Up, SwipeSettings::default())
        .with_swipe(SwipeDirection::Down, SwipeSettings::default())
        .map(|msg| matches!(msg, FrameMsg::Button(_)).then_some(FlowMsg::Info));

        let content_step_hold = Frame::left_aligned(
            TR::tutorial__title_hold.into(),
            SwipeContent::new(PromptScreen::new_hold_to_confirm()),
        )
        .with_footer(TR::instructions__exit_tutorial.into(), None)
        .map(|msg| matches!(msg, FrameMsg::Content(())).then_some(FlowMsg::Confirmed));

        let content_step_done = Frame::left_aligned(
            TR::tutorial__title_well_done.into(),
            SwipeContent::new(Paragraphs::new(Paragraph::new(
                &theme::TEXT_MAIN_GREY_LIGHT,
                TR::tutorial__ready_to_use_safe5,
            ))),
        )
        .with_footer(TR::instructions__swipe_up.into(), None)
        .with_swipe(SwipeDirection::Up, SwipeSettings::default())
        .map(|_| None);

        let content_menu = Frame::left_aligned(
            "".into(),
            VerticalMenu::empty()
                .item(theme::ICON_CHEVRON_RIGHT, TR::tutorial__did_you_know.into())
                .item(theme::ICON_REBOOT, TR::tutorial__restart_tutorial.into())
                .danger(theme::ICON_CANCEL, TR::tutorial__exit.into()),
        )
        .with_cancel_button()
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .with_swipe(SwipeDirection::Left, SwipeSettings::immediate())
        .map(|msg| match msg {
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
            FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
        });

        let content_did_you_know = Frame::left_aligned(
            "".into(),
            SwipeContent::new(Paragraphs::new(Paragraph::new(
                &theme::TEXT_MAIN_GREY_LIGHT,
                TR::tutorial__first_wallet,
            ))),
        )
        .with_cancel_button()
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| matches!(msg, FrameMsg::Button(_)).then_some(FlowMsg::Cancelled));

        let content_hold_to_exit = Frame::left_aligned(
            TR::tutorial__title_hold.into(),
            SwipeContent::new(PromptScreen::new_hold_to_confirm_danger()),
        )
        .with_footer(TR::instructions__exit_tutorial.into(), None)
        .map(|msg| matches!(msg, FrameMsg::Content(())).then_some(FlowMsg::Confirmed));

        let store = flow_store()
            .add(content_step_welcome)?
            .add(content_step_begin)?
            .add(content_step_navigation)?
            .add(content_step_menu)?
            .add(content_step_hold)?
            .add(content_step_done)?
            .add(content_menu)?
            .add(content_did_you_know)?
            .add(content_hold_to_exit)?;
        let res = SwipeFlow::new(ShowTutorial::StepWelcome, store)?;
        Ok(LayoutObj::new(res)?.into())
    }
}
