use crate::{
    error,
    maybe_trace::MaybeTrace,
    strutil::TString,
    translations::TR,
    ui::{
        component::{text::paragraphs::Paragraph, ComponentExt, SwipeDirection},
        flow::{base::Decision, FlowMsg, FlowState, FlowStore},
    },
};

use super::super::{
    component::{Frame, FrameMsg, PromptScreen, VerticalMenu, VerticalMenuChoiceMsg},
    theme,
};

// TODO: merge with code from https://github.com/trezor/trezor-firmware/pull/3805
// when ready

#[derive(Copy, Clone, PartialEq, Eq, ToPrimitive)]
pub enum ConfirmAction {
    Intro,
    Menu,
    Confirm,
}

/// ConfirmAction flow without a separate "Tap to confirm" or "Hold to confirm"
/// screen. Swiping up directly from the intro screen confirms action.
#[derive(Copy, Clone, PartialEq, Eq, ToPrimitive)]
pub enum ConfirmActionSimple {
    Intro,
    Menu,
}

impl FlowState for ConfirmAction {
    fn handle_swipe(&self, direction: SwipeDirection) -> Decision<Self> {
        match (self, direction) {
            (ConfirmAction::Intro, SwipeDirection::Left) => {
                Decision::Goto(ConfirmAction::Menu, direction)
            }
            (ConfirmAction::Menu, SwipeDirection::Right) => {
                Decision::Goto(ConfirmAction::Intro, direction)
            }
            (ConfirmAction::Intro, SwipeDirection::Up) => {
                Decision::Goto(ConfirmAction::Confirm, direction)
            }
            (ConfirmAction::Confirm, SwipeDirection::Down) => {
                Decision::Goto(ConfirmAction::Intro, direction)
            }
            (ConfirmAction::Confirm, SwipeDirection::Left) => {
                Decision::Goto(ConfirmAction::Menu, direction)
            }
            _ => Decision::Nothing,
        }
    }

    fn handle_event(&self, msg: FlowMsg) -> Decision<Self> {
        match (self, msg) {
            (ConfirmAction::Intro, FlowMsg::Info) => {
                Decision::Goto(ConfirmAction::Menu, SwipeDirection::Left)
            }
            (ConfirmAction::Menu, FlowMsg::Cancelled) => {
                Decision::Goto(ConfirmAction::Intro, SwipeDirection::Right)
            }
            (ConfirmAction::Menu, FlowMsg::Choice(0)) => Decision::Return(FlowMsg::Cancelled),
            (ConfirmAction::Menu, FlowMsg::Choice(1)) => Decision::Return(FlowMsg::Info),
            (ConfirmAction::Confirm, FlowMsg::Confirmed) => Decision::Return(FlowMsg::Confirmed),
            (ConfirmAction::Confirm, FlowMsg::Info) => {
                Decision::Goto(ConfirmAction::Menu, SwipeDirection::Left)
            }
            _ => Decision::Nothing,
        }
    }
}

impl FlowState for ConfirmActionSimple {
    fn handle_swipe(&self, direction: SwipeDirection) -> Decision<Self> {
        match (self, direction) {
            (ConfirmActionSimple::Intro, SwipeDirection::Left) => {
                Decision::Goto(ConfirmActionSimple::Menu, direction)
            }
            (ConfirmActionSimple::Menu, SwipeDirection::Right) => {
                Decision::Goto(ConfirmActionSimple::Intro, direction)
            }
            (ConfirmActionSimple::Intro, SwipeDirection::Up) => {
                Decision::Return(FlowMsg::Confirmed)
            }
            _ => Decision::Nothing,
        }
    }

    fn handle_event(&self, msg: FlowMsg) -> Decision<Self> {
        match (self, msg) {
            (ConfirmActionSimple::Intro, FlowMsg::Info) => {
                Decision::Goto(ConfirmActionSimple::Menu, SwipeDirection::Left)
            }
            (ConfirmActionSimple::Menu, FlowMsg::Cancelled) => {
                Decision::Goto(ConfirmActionSimple::Intro, SwipeDirection::Right)
            }
            (ConfirmActionSimple::Menu, FlowMsg::Choice(0)) => Decision::Return(FlowMsg::Cancelled),
            (ConfirmActionSimple::Menu, FlowMsg::Choice(1)) => Decision::Return(FlowMsg::Info),
            _ => Decision::Nothing,
        }
    }
}

use crate::{
    micropython::{map::Map, obj::Obj, qstr::Qstr, util},
    ui::{
        component::{
            swipe_detect::SwipeSettings,
            text::paragraphs::{ParagraphSource, ParagraphVecShort, VecExt},
            Component, Paginate,
        },
        flow::{flow_store, SwipeFlow, SwipePage},
        layout::obj::LayoutObj,
        model_mercury::component::SwipeContent,
    },
};

#[allow(clippy::not_unsafe_ptr_arg_deref)]
pub extern "C" fn new_confirm_action(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, new_confirm_action_obj) }
}

fn new_confirm_action_obj(_args: &[Obj], kwargs: &Map) -> Result<Obj, error::Error> {
    let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
    let action: Option<TString> = kwargs.get(Qstr::MP_QSTR_action)?.try_into_option()?;
    let description: Option<TString> = kwargs.get(Qstr::MP_QSTR_description)?.try_into_option()?;
    let subtitle: Option<TString> = kwargs
        .get(Qstr::MP_QSTR_subtitle)
        .unwrap_or(Obj::const_none())
        .try_into_option()?;
    // let verb: Option<TString> = kwargs
    //     .get(Qstr::MP_QSTR_verb)
    //     .unwrap_or_else(|_| Obj::const_none())
    //     .try_into_option()?;
    let verb_cancel: Option<TString> = kwargs
        .get(Qstr::MP_QSTR_verb_cancel)
        .unwrap_or_else(|_| Obj::const_none())
        .try_into_option()?;
    let reverse: bool = kwargs.get_or(Qstr::MP_QSTR_reverse, false)?;
    let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;
    // let hold_danger: bool = kwargs.get_or(Qstr::MP_QSTR_hold_danger, false)?;
    let prompt_screen: bool = kwargs.get_or(Qstr::MP_QSTR_prompt_screen, false)?;
    let prompt_title: TString = kwargs.get_or(Qstr::MP_QSTR_prompt_title, title)?;

    let paragraphs = {
        let action = action.unwrap_or("".into());
        let description = description.unwrap_or("".into());
        let mut paragraphs = ParagraphVecShort::new();
        if !reverse {
            paragraphs
                .add(Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, action))
                .add(Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, description));
        } else {
            paragraphs
                .add(Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, description))
                .add(Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, action));
        }
        paragraphs.into_paragraphs()
    };

    new_confirm_action_simple(
        paragraphs,
        title,
        subtitle,
        verb_cancel,
        prompt_screen.then_some(prompt_title),
        hold,
        false,
    )
}

#[inline(never)]
pub fn new_confirm_action_uni<T: Component + MaybeTrace + 'static>(
    content: T,
    title: TString<'static>,
    subtitle: Option<TString<'static>>,
    verb_cancel: Option<TString<'static>>,
    prompt_screen: Option<TString<'static>>,
    hold: bool,
    info: bool,
) -> Result<Obj, error::Error> {
    let mut content_intro = Frame::left_aligned(title, content)
        .with_menu_button()
        .with_footer(TR::instructions__swipe_up.into(), None)
        .with_swipe(SwipeDirection::Up, SwipeSettings::default())
        .with_swipe(SwipeDirection::Left, SwipeSettings::default())
        .with_vertical_pages();

    if let Some(subtitle) = subtitle {
        content_intro = content_intro.with_subtitle(subtitle);
    }

    let prompt_screen = prompt_screen.or_else(|| hold.then_some(title));
    let prompt_pages: usize = prompt_screen.is_some().into();
    let content_intro = content_intro
        .map(move |msg| match msg {
            FrameMsg::Button(_) => Some(FlowMsg::Info),
            _ => None,
        })
        .with_pages(move |intro_pages| intro_pages + prompt_pages);

    let mut menu_choices = VerticalMenu::empty().danger(
        theme::ICON_CANCEL,
        verb_cancel.unwrap_or(TR::buttons__cancel.into()),
    );
    if info {
        menu_choices = menu_choices.item(
            theme::ICON_CHEVRON_RIGHT,
            TR::words__title_information.into(),
        );
    }
    let content_menu = Frame::left_aligned("".into(), menu_choices)
        .with_cancel_button()
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(move |msg| match msg {
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
            FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
        });

    if let Some(prompt_title) = prompt_screen {
        let (prompt, prompt_action) = if hold {
            (
                PromptScreen::new_hold_to_confirm(),
                TR::instructions__hold_to_confirm.into(),
            )
        } else {
            (
                PromptScreen::new_tap_to_confirm(),
                TR::instructions__tap_to_confirm.into(),
            )
        };

        let mut content_confirm = Frame::left_aligned(prompt_title, SwipeContent::new(prompt))
            .with_footer(prompt_action, None)
            .with_menu_button()
            .with_swipe(SwipeDirection::Down, SwipeSettings::default())
            .with_swipe(SwipeDirection::Left, SwipeSettings::default());

        if let Some(subtitle) = subtitle {
            content_confirm = content_confirm.with_subtitle(subtitle);
        }

        let content_confirm = content_confirm.map(move |msg| match msg {
            FrameMsg::Content(()) => Some(FlowMsg::Confirmed),
            FrameMsg::Button(_) => Some(FlowMsg::Info),
        });

        let store = flow_store()
            .add(content_intro)?
            .add(content_menu)?
            .add(content_confirm)?;
        let res = SwipeFlow::new(ConfirmAction::Intro, store)?;
        Ok(LayoutObj::new(res)?.into())
    } else {
        let store = flow_store().add(content_intro)?.add(content_menu)?;
        let res = SwipeFlow::new(ConfirmActionSimple::Intro, store)?;
        Ok(LayoutObj::new(res)?.into())
    }
}

#[inline(never)]
pub fn new_confirm_action_simple<T: Component + Paginate + MaybeTrace + 'static>(
    content: T,
    title: TString<'static>,
    subtitle: Option<TString<'static>>,
    verb_cancel: Option<TString<'static>>,
    prompt_screen: Option<TString<'static>>,
    hold: bool,
    info: bool,
) -> Result<Obj, error::Error> {
    new_confirm_action_uni(
        SwipeContent::new(SwipePage::vertical(content)),
        title,
        subtitle,
        verb_cancel,
        prompt_screen,
        hold,
        info,
    )
}
