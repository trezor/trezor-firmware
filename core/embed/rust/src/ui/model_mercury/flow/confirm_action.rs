use crate::{
    error::{self, Error},
    maybe_trace::MaybeTrace,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            swipe_detect::SwipeSettings,
            text::paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort, VecExt},
            Component, ComponentExt, EventCtx, Paginate,
        },
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow, SwipePage,
        },
        geometry::Direction,
    },
};

use super::super::{
    component::{
        Footer, Frame, FrameMsg, PromptMsg, PromptScreen, SwipeContent, VerticalMenu,
        VerticalMenuChoiceMsg,
    },
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmAction {
    Intro,
    Menu,
    Confirm,
}

impl FlowController for ConfirmAction {
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Intro, Direction::Left) => Self::Menu.swipe(direction),
            (Self::Menu, Direction::Right) => Self::Intro.swipe(direction),
            (Self::Intro, Direction::Up) => Self::Confirm.swipe(direction),
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
            (Self::Menu, FlowMsg::Choice(1)) => self.return_msg(FlowMsg::Info),
            (Self::Confirm, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            (Self::Confirm, FlowMsg::Info) => Self::Menu.goto(),
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

impl FlowController for ConfirmActionSimple {
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
            (Self::Menu, FlowMsg::Choice(1)) => self.return_msg(FlowMsg::Info),
            _ => self.do_nothing(),
        }
    }
}

pub struct ConfirmActionMenu {
    verb_cancel: Option<TString<'static>>,
    info: bool,
    verb_info: Option<TString<'static>>,
}

impl ConfirmActionMenu {
    pub fn new(
        verb_cancel: Option<TString<'static>>,
        info: bool,
        verb_info: Option<TString<'static>>,
    ) -> Self {
        Self {
            verb_cancel,
            info,
            verb_info,
        }
    }
}

pub struct ConfirmActionStrings {
    title: TString<'static>,
    subtitle: Option<TString<'static>>,
    verb: Option<TString<'static>>,
    prompt_screen: Option<TString<'static>>,
}

impl ConfirmActionStrings {
    pub fn new(
        title: TString<'static>,
        subtitle: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        prompt_screen: Option<TString<'static>>,
    ) -> Self {
        Self {
            title,
            subtitle,
            verb,
            prompt_screen,
        }
    }
}

#[allow(clippy::too_many_arguments)]
pub fn new_confirm_action(
    title: TString<'static>,
    action: Option<TString<'static>>,
    description: Option<TString<'static>>,
    subtitle: Option<TString<'static>>,
    verb_cancel: Option<TString<'static>>,
    reverse: bool,
    hold: bool,
    prompt_screen: bool,
    prompt_title: TString<'static>,
) -> Result<SwipeFlow, error::Error> {
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
        ConfirmActionMenu::new(verb_cancel, false, None),
        ConfirmActionStrings::new(title, subtitle, None, prompt_screen.then_some(prompt_title)),
        hold,
        None,
        false,
    )
}

#[inline(never)]
fn new_confirm_action_uni<T: Component + Paginate + MaybeTrace + 'static>(
    content: SwipeContent<SwipePage<T>>,
    menu: ConfirmActionMenu,
    strings: ConfirmActionStrings,
    hold: bool,
    page_counter: bool,
) -> Result<SwipeFlow, error::Error> {
    let (prompt_screen, prompt_pages, flow, page) =
        create_flow(strings.title, strings.prompt_screen, hold);

    let mut content_intro = Frame::left_aligned(strings.title, content)
        .with_swipe(Direction::Up, SwipeSettings::default())
        .with_swipe(Direction::Left, SwipeSettings::default())
        .with_vertical_pages()
        .with_menu_button()
        .with_footer(TR::instructions__swipe_up.into(), None);

    if page_counter {
        fn footer_update_fn<T: Component + Paginate>(
            content: &SwipeContent<SwipePage<T>>,
            ctx: &mut EventCtx,
            footer: &mut Footer,
        ) {
            let current_page = content.inner().current_page();
            let page_count = content.inner().page_count();
            footer.update_page_counter(ctx, current_page, page_count);
        }

        content_intro = content_intro
            .with_footer_counter(TR::instructions__swipe_up.into())
            .register_footer_update_fn(footer_update_fn::<T>);
    }

    if let Some(subtitle) = strings.subtitle {
        content_intro = content_intro.with_subtitle(subtitle);
    }

    let content_intro = content_intro
        .map(move |msg| match msg {
            FrameMsg::Button(_) => Some(FlowMsg::Info),
            _ => None,
        })
        .with_pages(move |intro_pages| intro_pages + prompt_pages);

    let flow = flow?.with_page(page, content_intro)?;

    let flow = create_menu(flow, menu, prompt_screen)?;

    let flow = create_confirm(flow, strings.subtitle, hold, prompt_screen)?;

    Ok(flow)
}

fn create_flow(
    title: TString<'static>,
    prompt_screen: Option<TString<'static>>,
    hold: bool,
) -> (
    Option<TString<'static>>,
    usize,
    Result<SwipeFlow, Error>,
    &'static dyn FlowController,
) {
    let prompt_screen = prompt_screen.or_else(|| hold.then_some(title));
    let prompt_pages: usize = prompt_screen.is_some().into();

    let (flow, page): (Result<SwipeFlow, Error>, &dyn FlowController) = if prompt_screen.is_some() {
        (SwipeFlow::new(&ConfirmAction::Intro), &ConfirmAction::Intro)
    } else {
        (
            SwipeFlow::new(&ConfirmActionSimple::Intro),
            &ConfirmActionSimple::Intro,
        )
    };

    (prompt_screen, prompt_pages, flow, page)
}

fn create_menu(
    flow: SwipeFlow,
    menu: ConfirmActionMenu,
    prompt_screen: Option<TString<'static>>,
) -> Result<SwipeFlow, Error> {
    let mut menu_choices = VerticalMenu::empty().danger(
        theme::ICON_CANCEL,
        menu.verb_cancel.unwrap_or(TR::buttons__cancel.into()),
    );

    if menu.info {
        menu_choices = menu_choices.item(
            theme::ICON_CHEVRON_RIGHT,
            menu.verb_info
                .unwrap_or(TR::words__title_information.into()),
        );
    }

    let content_menu = Frame::left_aligned("".into(), menu_choices)
        .with_cancel_button()
        .with_swipe(Direction::Right, SwipeSettings::immediate());

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
            .with_swipe(Direction::Down, SwipeSettings::default())
            .with_swipe(Direction::Left, SwipeSettings::default());

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
    menu: ConfirmActionMenu,
    strings: ConfirmActionStrings,
    hold: bool,
    page_limit: Option<usize>,
    page_counter: bool,
) -> Result<SwipeFlow, error::Error> {
    new_confirm_action_uni(
        SwipeContent::new(SwipePage::vertical(content).with_limit(page_limit)),
        menu,
        strings,
        hold,
        page_counter,
    )
}
