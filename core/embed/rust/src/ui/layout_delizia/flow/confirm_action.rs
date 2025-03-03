use heapless::Vec;

use crate::{
    error::{self, Error},
    maybe_trace::MaybeTrace,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            swipe_detect::SwipeSettings,
            text::paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort, VecExt},
            Component, ComponentExt, EventCtx, PaginateFull,
        },
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow, SwipePage,
        },
        geometry::Direction,
    },
};

use super::super::{
    component::{Footer, Frame, PromptScreen, SwipeContent, VerticalMenu, VerticalMenuChoiceMsg},
    theme,
};

const MENU_ITEM_CANCEL: usize = 0;
const MENU_ITEM_INFO: usize = 1;

// Extra button at the top-right corner of the Action screen
#[derive(PartialEq)]
pub enum ConfirmActionExtra {
    // Opens a menu which can (optionally) lead to an extra Info screen, or cancel the action
    Menu(ConfirmActionMenuStrings),
    // Shows a cancel button directly
    Cancel,
}

pub struct ConfirmActionStrings {
    title: TString<'static>,
    subtitle: Option<TString<'static>>,
    verb: Option<TString<'static>>,
    prompt_screen: Option<TString<'static>>,
    footer_description: Option<TString<'static>>,
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
            footer_description: None,
        }
    }

    pub fn with_footer_description(mut self, footer_description: Option<TString<'static>>) -> Self {
        self.footer_description = footer_description;
        self
    }
}

#[derive(PartialEq)]
pub struct ConfirmActionMenuStrings {
    verb_cancel: TString<'static>,
    verb_info: Option<TString<'static>>,
}

impl ConfirmActionMenuStrings {
    pub fn new() -> Self {
        Self {
            verb_cancel: TR::buttons__cancel.into(),
            verb_info: None,
        }
    }

    pub fn with_verb_cancel(mut self, verb_cancel: Option<TString<'static>>) -> Self {
        self.verb_cancel = verb_cancel.unwrap_or(TR::buttons__cancel.into());
        self
    }

    pub const fn with_verb_info(mut self, verb_info: Option<TString<'static>>) -> Self {
        self.verb_info = verb_info;
        self
    }
}

/// The simplest form of the ConfirmAction flow:
/// no menu, nor a separate "Tap to confirm" or "Hold to confirm".
#[derive(Copy, Clone, PartialEq, Eq)]
enum ConfirmAction {
    Action,
}

impl FlowController for ConfirmAction {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Action, Direction::Up) => self.return_msg(FlowMsg::Confirmed),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Action, FlowMsg::Cancelled) => self.return_msg(FlowMsg::Cancelled),
            _ => self.do_nothing(),
        }
    }
}

// A ConfirmAction flow with  a separate "Tap to confirm" or "Hold to confirm"
// screen.
#[derive(Copy, Clone, PartialEq, Eq)]
enum ConfirmActionWithConfirmation {
    Action,
    Confirmation,
}

impl FlowController for ConfirmActionWithConfirmation {
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Action, Direction::Up) => Self::Confirmation.swipe(direction),
            (Self::Confirmation, Direction::Down) => Self::Action.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Action, FlowMsg::Cancelled) => self.return_msg(FlowMsg::Cancelled),
            (Self::Confirmation, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            _ => self.do_nothing(),
        }
    }
}

/// A ConfirmAction flow with a menu which can contain various items
/// as defined by ConfirmActionExtra::Menu.
#[derive(Copy, Clone, PartialEq, Eq)]
enum ConfirmActionWithMenu {
    Action,
    Menu,
}

impl FlowController for ConfirmActionWithMenu {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Action, Direction::Left) => Self::Menu.swipe(direction),
            (Self::Menu, Direction::Right) => Self::Action.swipe(direction),
            (Self::Action, Direction::Up) => self.return_msg(FlowMsg::Confirmed),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Action, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Action.swipe_right(),
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_CANCEL)) => self.return_msg(FlowMsg::Cancelled),
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_INFO)) => self.return_msg(FlowMsg::Info),
            _ => self.do_nothing(),
        }
    }
}

// A ConfirmAction flow with a menu and
// a separate "Tap to confirm" or "Hold to confirm" screen.
#[derive(Copy, Clone, PartialEq, Eq)]
enum ConfirmActionWithMenuAndConfirmation {
    Action,
    Menu,
    Confirmation,
}

impl FlowController for ConfirmActionWithMenuAndConfirmation {
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Action, Direction::Left) => Self::Menu.swipe(direction),
            (Self::Menu, Direction::Right) => Self::Action.swipe(direction),
            (Self::Action, Direction::Up) => Self::Confirmation.swipe(direction),
            (Self::Confirmation, Direction::Down) => Self::Action.swipe(direction),
            (Self::Confirmation, Direction::Left) => Self::Menu.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Action, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Action.swipe_right(),
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_CANCEL)) => self.return_msg(FlowMsg::Cancelled),
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_INFO)) => self.return_msg(FlowMsg::Info),
            (Self::Confirmation, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            (Self::Confirmation, FlowMsg::Info) => Self::Menu.goto(),
            _ => self.do_nothing(),
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
        ConfirmActionExtra::Menu(ConfirmActionMenuStrings::new().with_verb_cancel(verb_cancel)),
        ConfirmActionStrings::new(title, subtitle, None, prompt_screen.then_some(prompt_title)),
        hold,
        None,
        0,
        false,
    )
}

#[inline(never)]
fn new_confirm_action_uni<T: Component + PaginateFull + MaybeTrace + 'static>(
    content: SwipeContent<SwipePage<T>>,
    extra: ConfirmActionExtra,
    strings: ConfirmActionStrings,
    hold: bool,
    frame_margin: usize,
    page_counter: bool,
) -> Result<SwipeFlow, error::Error> {
    let (prompt_screen, prompt_pages, flow, page) =
        create_flow(strings.title, strings.prompt_screen, hold, &extra);

    let mut content = Frame::left_aligned(strings.title, content)
        .with_margin(frame_margin)
        .with_swipeup_footer(strings.footer_description)
        .with_vertical_pages();

    match extra {
        ConfirmActionExtra::Menu { .. } => {
            content = content
                .with_menu_button()
                .with_swipe(Direction::Left, SwipeSettings::default());
        }
        ConfirmActionExtra::Cancel => {
            content = content.with_cancel_button();
        }
    }

    if page_counter {
        fn footer_update_fn<T: Component + PaginateFull>(
            content: &SwipeContent<SwipePage<T>>,
            ctx: &mut EventCtx,
            footer: &mut Footer,
        ) {
            footer.update_pager(ctx, content.inner().pager());
        }

        content = content
            .with_footer_counter(TR::instructions__tap_to_continue.into())
            .register_footer_update_fn(footer_update_fn::<T>);
    }

    if let Some(subtitle) = strings.subtitle {
        content = content.with_subtitle(subtitle);
    }

    let content = content
        .map_to_button_msg()
        .with_pages(move |intro_pages| intro_pages + prompt_pages);

    let mut flow = flow?;
    flow.add_page(page, content)?;
    create_menu(&mut flow, &extra, prompt_screen)?;
    create_confirm(&mut flow, &extra, strings.subtitle, hold, prompt_screen)?;

    Ok(flow)
}

fn create_flow(
    title: TString<'static>,
    prompt_screen: Option<TString<'static>>,
    hold: bool,
    extra: &ConfirmActionExtra,
) -> (
    Option<TString<'static>>,
    usize,
    Result<SwipeFlow, Error>,
    &'static dyn FlowController,
) {
    let prompt_screen = prompt_screen.or_else(|| hold.then_some(title));
    let prompt_pages: usize = prompt_screen.is_some().into();
    let initial_page: &dyn FlowController = match (extra, prompt_screen.is_some()) {
        (ConfirmActionExtra::Menu { .. }, false) => &ConfirmActionWithMenu::Action,
        (ConfirmActionExtra::Menu { .. }, true) => &ConfirmActionWithMenuAndConfirmation::Action,
        (ConfirmActionExtra::Cancel, false) => &ConfirmAction::Action,
        (ConfirmActionExtra::Cancel, true) => &ConfirmActionWithConfirmation::Action,
    };

    (
        prompt_screen,
        prompt_pages,
        SwipeFlow::new(initial_page),
        initial_page,
    )
}

fn create_menu(
    flow: &mut SwipeFlow,
    extra: &ConfirmActionExtra,
    prompt_screen: Option<TString<'static>>,
) -> Result<(), Error> {
    if let ConfirmActionExtra::Menu(menu_strings) = extra {
        let mut menu = VerticalMenu::empty();
        let mut menu_items = Vec::<usize, 2>::new();

        if let Some(verb_info) = menu_strings.verb_info {
            menu = menu.item(theme::ICON_CHEVRON_RIGHT, verb_info);
            unwrap!(menu_items.push(MENU_ITEM_INFO));
        }

        menu = menu.danger(theme::ICON_CANCEL, menu_strings.verb_cancel);
        unwrap!(menu_items.push(MENU_ITEM_CANCEL));

        let content_menu = Frame::left_aligned("".into(), menu)
            .with_cancel_button()
            .with_swipe(Direction::Right, SwipeSettings::immediate());

        let content_menu = content_menu.map(move |msg| match msg {
            VerticalMenuChoiceMsg::Selected(i) => {
                let selected_item = menu_items[i];
                Some(FlowMsg::Choice(selected_item))
            }
        });

        if prompt_screen.is_some() {
            flow.add_page(&ConfirmActionWithMenuAndConfirmation::Menu, content_menu)?;
        } else {
            flow.add_page(&ConfirmActionWithMenu::Menu, content_menu)?;
        }
    }
    Ok(())
}

// Create the extra confirmation screen (optional).
fn create_confirm(
    flow: &mut SwipeFlow,
    extra: &ConfirmActionExtra,
    subtitle: Option<TString<'static>>,
    hold: bool,
    prompt_screen: Option<TString<'static>>,
) -> Result<(), Error> {
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
            .with_swipe(Direction::Down, SwipeSettings::default())
            .with_swipe(Direction::Left, SwipeSettings::default());

        if matches!(extra, ConfirmActionExtra::Menu(_)) {
            content_confirm = content_confirm.with_menu_button();
        }

        if let Some(subtitle) = subtitle {
            content_confirm = content_confirm.with_subtitle(subtitle);
        }

        let content_confirm = content_confirm.map(super::util::map_to_confirm);

        flow.add_page(
            &ConfirmActionWithMenuAndConfirmation::Confirmation,
            content_confirm,
        )?;
    }
    Ok(())
}

#[inline(never)]
pub fn new_confirm_action_simple<T: Component + PaginateFull + MaybeTrace + 'static>(
    content: T,
    extra: ConfirmActionExtra,
    strings: ConfirmActionStrings,
    hold: bool,
    page_limit: Option<u16>,
    frame_margin: usize,
    page_counter: bool,
) -> Result<SwipeFlow, error::Error> {
    new_confirm_action_uni(
        SwipeContent::new(SwipePage::vertical(content).with_limit(page_limit)),
        extra,
        strings,
        hold,
        frame_margin,
        page_counter,
    )
}
