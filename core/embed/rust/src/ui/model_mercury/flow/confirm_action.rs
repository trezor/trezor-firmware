use crate::{
    error,
    error::Error,
    maybe_trace::MaybeTrace,
    micropython::{map::Map, obj::Obj, qstr::Qstr, util},
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            swipe_detect::SwipeSettings,
            text::paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort, VecExt},
            Component, ComponentExt, Paginate, SwipeDirection,
        },
        flow::{
            base::{DecisionBuilder as _, StateChange},
            FlowMsg, FlowState, SwipeFlow, SwipePage,
        },
        layout::obj::LayoutObj,
    },
};

use super::super::{
    component::{
        Frame, FrameMsg, PromptMsg, PromptScreen, SwipeContent, VerticalMenu, VerticalMenuChoiceMsg,
    },
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmAction {
    Intro,
    Menu,
    Confirm,
}

impl FlowState for ConfirmAction {
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: SwipeDirection) -> StateChange {
        match (self, direction) {
            (Self::Intro, SwipeDirection::Left) => Self::Menu.swipe(direction),
            (Self::Menu, SwipeDirection::Right) => Self::Intro.swipe(direction),
            (Self::Intro, SwipeDirection::Up) => Self::Confirm.swipe(direction),
            (Self::Confirm, SwipeDirection::Down) => Self::Intro.swipe(direction),
            (Self::Confirm, SwipeDirection::Left) => Self::Menu.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> StateChange {
        match (self, msg) {
            (Self::Intro, FlowMsg::Info) => Self::Menu.transit(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Intro.swipe_right(),
            (Self::Menu, FlowMsg::Choice(0)) => self.return_msg(FlowMsg::Cancelled),
            (Self::Menu, FlowMsg::Choice(1)) => self.return_msg(FlowMsg::Info),
            (Self::Confirm, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            (Self::Confirm, FlowMsg::Info) => Self::Menu.transit(),
            _ => self.do_nothing(),
        }
    }
}

/// ConfirmAction flow without a separate "Tap to confirm" or "Hold to confirm"
/// screen. Swiping up directly from the intro screen confirms action.
#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmActionSimple {
    Intro,
    Menu,
}

impl FlowState for ConfirmActionSimple {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: SwipeDirection) -> StateChange {
        match (self, direction) {
            (Self::Intro, SwipeDirection::Left) => Self::Menu.swipe(direction),
            (Self::Menu, SwipeDirection::Right) => Self::Intro.swipe(direction),
            (Self::Intro, SwipeDirection::Up) => self.return_msg(FlowMsg::Confirmed),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> StateChange {
        match (self, msg) {
            (Self::Intro, FlowMsg::Info) => Self::Menu.transit(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Intro.swipe_right(),
            (Self::Menu, FlowMsg::Choice(0)) => self.return_msg(FlowMsg::Cancelled),
            (Self::Menu, FlowMsg::Choice(1)) => self.return_msg(FlowMsg::Info),
            _ => self.do_nothing(),
        }
    }
}

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
    let (prompt_screen, prompt_pages, flow, page) = create_flow(title, prompt_screen, hold);

    let mut content_intro = Frame::left_aligned(title, content)
        .with_menu_button()
        .with_footer(TR::instructions__swipe_up.into(), None)
        .with_swipe(SwipeDirection::Up, SwipeSettings::default())
        .with_swipe(SwipeDirection::Left, SwipeSettings::default())
        .with_vertical_pages();

    if let Some(subtitle) = subtitle {
        content_intro = content_intro.with_subtitle(subtitle);
    }

    let content_intro = content_intro
        .map(move |msg| match msg {
            FrameMsg::Button(_) => Some(FlowMsg::Info),
            _ => None,
        })
        .with_pages(move |intro_pages| intro_pages + prompt_pages);

    let flow = flow?.with_page(page, content_intro)?;

    create_menu_and_confirm(subtitle, verb_cancel, hold, info, prompt_screen, flow)
}

fn create_flow(
    title: TString<'static>,
    prompt_screen: Option<TString<'static>>,
    hold: bool,
) -> (
    Option<TString<'static>>,
    usize,
    Result<SwipeFlow, Error>,
    &'static dyn FlowState,
) {
    let prompt_screen = prompt_screen.or_else(|| hold.then_some(title));
    let prompt_pages: usize = prompt_screen.is_some().into();

    let flow = if prompt_screen.is_some() {
        SwipeFlow::new(&ConfirmAction::Intro)
    } else {
        SwipeFlow::new(&ConfirmActionSimple::Intro)
    };

    let page: &dyn FlowState = if prompt_screen.is_some() {
        &ConfirmAction::Intro
    } else {
        &ConfirmActionSimple::Intro
    };

    (prompt_screen, prompt_pages, flow, page)
}

fn create_menu_and_confirm(
    subtitle: Option<TString<'static>>,
    verb_cancel: Option<TString<'static>>,
    hold: bool,
    info: bool,
    prompt_screen: Option<TString<'static>>,
    flow: SwipeFlow,
) -> Result<Obj, Error> {
    let flow = create_menu(flow, verb_cancel, info, prompt_screen)?;

    let flow = create_confirm(flow, subtitle, hold, prompt_screen)?;

    Ok(LayoutObj::new(flow)?.into())
}

fn create_menu(
    flow: SwipeFlow,
    verb_cancel: Option<TString<'static>>,
    info: bool,
    prompt_screen: Option<TString<'static>>,
) -> Result<SwipeFlow, Error> {
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
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate());

    let content_menu = content_menu.map(move |msg| match msg {
        FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
        FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
    });

    if prompt_screen.is_some() {
        flow.with_page(&ConfirmAction::Menu, content_menu)
    } else {
        flow.with_page(&ConfirmActionSimple::Menu, content_menu)
    }
}

fn create_confirm(
    flow: SwipeFlow,
    subtitle: Option<TString<'static>>,
    hold: bool,
    prompt_screen: Option<TString<'static>>,
) -> Result<SwipeFlow, Error> {
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
            FrameMsg::Content(PromptMsg::Confirmed) => Some(FlowMsg::Confirmed),
            FrameMsg::Button(_) => Some(FlowMsg::Info),
            _ => None,
        });

        flow.with_page(&ConfirmAction::Confirm, content_confirm)
    } else {
        Ok(flow)
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
