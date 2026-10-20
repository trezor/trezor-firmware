use heapless::Vec;

use super::super::fonts;
use super::{
    theme, ButtonDetails, ButtonPage, ButtonPos, CancelConfirmMsg, ChoiceMsg, MenuNav,
    ScrollableFrame, SimpleChoice,
};
use crate::strutil::TString;
use crate::translations::TR;
use crate::ui::component::text::op::OpTextLayout;
use crate::ui::component::{Component, Event, EventCtx, FormattedText, Never, Pad, PageMsg};
use crate::ui::event::{ButtonEvent, PhysicalButton};
use crate::ui::geometry::Rect;
use crate::ui::shape::Renderer;

/// Screens of the tutorial, in the order they are shown.
#[derive(Clone, Copy, PartialEq, Eq)]
enum Screen {
    Welcome,
    /// "Skip tutorial?", from the cross on `Welcome`
    Skip,
    Buttons,
    HoldToConfirm,
    /// Pressing both buttons. `hint` is the button that was pressed and
    /// released alone.
    MiddleButton {
        hint: Option<ButtonPos>,
    },
    Scroll,
    /// Teaching "Shift" - the right button alone does nothing.
    GoBack,
    Remember,
    MenuIntro,
    /// The tutorial context menu, see `MENU_COMPLETE` and `MENU_RESTART`
    Menu,
    Complete,
    /// Information about the menu, from the menu button of the other screens.
    /// Goes back to `Tutorial::info_from`.
    MenuInfo,
}

/// Items of the tutorial menu
const MENU_COMPLETE: usize = 0;
const MENU_RESTART: usize = 1;

type TutorialPage = ScrollableFrame<ButtonPage<FormattedText>>;

// Most of the screens are pages, boxing them would not save anything.
#[allow(clippy::large_enum_variant)]
enum Content {
    Page(TutorialPage),
    Menu(SimpleChoice),
}

enum ContentMsg {
    Page(PageMsg<Never>),
    Menu(ChoiceMsg<usize>),
}

/// Caesar device tutorial (Figma "ExternalMenu / Tutorial update").
///
/// One layout switching between the screens (`Screen`). Each screen is a
/// `ButtonPage` in a `ScrollableFrame`, the tutorial menu is the regular
/// context menu (`SimpleChoice::menu`). Finishing it is `Confirmed`, skipping
/// it `Cancelled`.
///
/// The menu button on the screens is `MenuNav::ChoiceMenu`, so that the
/// automated tests do not try to visit it as an information menu - it opens
/// the information screen or the tutorial menu instead.
///
/// Added elsewhere only for the tutorial: `ButtonPage::with_middle_btn`,
/// `ButtonDetails::ghost` and `ButtonDetails::with_pressed_arm`.
pub struct Tutorial {
    screen: Screen,
    /// Where `Screen::MenuInfo` goes back to
    info_from: Screen,
    content: Content,
    pad: Pad,
    bounds: Rect,
    single_press: SinglePress,
}

impl Tutorial {
    pub fn new() -> Self {
        Self {
            screen: Screen::Welcome,
            info_from: Screen::Welcome,
            content: Self::content(Screen::Welcome),
            pad: Pad::with_background(theme::BG),
            bounds: Rect::zero(),
            single_press: SinglePress::default(),
        }
    }

    fn go_to(&mut self, ctx: &mut EventCtx, screen: Screen) {
        self.screen = screen;
        self.content = Self::content(screen);
        self.place(self.bounds);
        // Buttons still held from the previous screen are not a single press
        self.single_press = SinglePress::default();
        self.pad.clear();
        ctx.request_paint();
    }

    /// The screen following `self.screen` after `msg`, `Err` when the
    /// tutorial ends.
    fn next(&mut self, msg: ContentMsg) -> Result<Option<Screen>, CancelConfirmMsg> {
        use ContentMsg as Msg;
        use Screen::*;

        let next = match (self.screen, msg) {
            // Cross on the first screen
            (Welcome, Msg::Page(PageMsg::Cancelled)) => Skip,
            (Skip, Msg::Page(PageMsg::Confirmed)) => return Err(CancelConfirmMsg::Cancelled),
            (Skip, Msg::Page(PageMsg::Cancelled)) => Welcome,

            (Welcome, Msg::Page(PageMsg::Confirmed)) => Buttons,
            (Buttons, Msg::Page(PageMsg::Confirmed)) => HoldToConfirm,
            (HoldToConfirm, Msg::Page(PageMsg::Confirmed)) => MiddleButton { hint: None },
            (MiddleButton { .. }, Msg::Page(PageMsg::Confirmed)) => Scroll,
            (Scroll, Msg::Page(PageMsg::Confirmed)) => GoBack,
            // The right button alone does nothing when teaching "Shift"
            (GoBack, Msg::Page(PageMsg::Confirmed)) => return Ok(None),
            (Remember, Msg::Page(PageMsg::Confirmed)) => MenuIntro,
            (Complete, Msg::Page(PageMsg::Confirmed)) => return Err(CancelConfirmMsg::Confirmed),

            // "Shift" + right button. On `GoBack` it continues, the screen is
            // teaching it.
            (GoBack, Msg::Page(PageMsg::Cancelled)) => Remember,
            (Remember, Msg::Page(PageMsg::Cancelled)) => GoBack,
            (MenuIntro, Msg::Page(PageMsg::Cancelled)) => Remember,

            // Menu button
            (MenuIntro, Msg::Page(PageMsg::Info)) => Menu,
            (screen, Msg::Page(PageMsg::Info)) => {
                self.info_from = screen;
                MenuInfo
            }
            (MenuInfo, Msg::Page(PageMsg::Cancelled)) => self.info_from,

            (Menu, Msg::Menu(ChoiceMsg::Choice { item, .. })) if item == MENU_COMPLETE => Complete,
            (Menu, Msg::Menu(ChoiceMsg::Choice { item, .. })) if item == MENU_RESTART => Welcome,
            (Menu, Msg::Menu(ChoiceMsg::Cancel)) => MenuIntro,

            // "Again"
            (Complete, Msg::Page(PageMsg::Cancelled)) => Welcome,
            _ => return Ok(None),
        };
        Ok(Some(next))
    }

    fn content(screen: Screen) -> Content {
        let page = match screen {
            Screen::Welcome => framed(
                Some(TR::tutorial__title_welcome),
                text(&[TR::tutorial__lets_begin])
                    .with_menu_nav(MenuNav::Close)
                    .with_confirm_btn(Some(ButtonDetails::scroll_down_wide())),
            ),
            Screen::Skip => framed(
                Some(TR::tutorial__title_skip),
                text(&[TR::tutorial__sure_you_want_skip])
                    .with_cancel_btn(Some(ButtonDetails::left_arrow_icon()))
                    .with_confirm_btn(Some(button_text(TR::buttons__skip))),
            ),
            Screen::Buttons => framed(
                None,
                text(&[TR::tutorial__use_trezor])
                    .with_menu_nav(MenuNav::ChoiceMenu)
                    .with_confirm_btn(Some(button_text(TR::buttons__continue))),
            ),
            Screen::HoldToConfirm => framed(
                Some(TR::instructions__hold_to_confirm),
                text(&[TR::tutorial__press_and_hold])
                    .with_menu_nav(MenuNav::ChoiceMenu)
                    .with_confirm_btn(Some(
                        button_text(TR::buttons__hold_to_confirm).with_default_duration(),
                    )),
            ),
            Screen::MiddleButton { hint } => framed(
                Some(TR::tutorial__title_middle_button),
                text(&[if hint.is_some() {
                    TR::tutorial__press_both
                } else {
                    TR::tutorial__middle_click
                }])
                .with_cancel_btn(None)
                .with_confirm_btn(None)
                .with_middle_btn(Some(
                    ButtonDetails::armed_text(TR::buttons__view.into()).with_pressed_arm(hint),
                )),
            ),
            Screen::Scroll => framed(
                Some(TR::tutorial__title_screen_scroll),
                text(&[TR::tutorial__scroll_down])
                    .with_menu_nav(MenuNav::ChoiceMenu)
                    .with_confirm_btn(Some(ButtonDetails::scroll_down_wide())),
            ),
            Screen::GoBack => framed(
                Some(TR::tutorial__title_go_back),
                text(&[TR::tutorial__hold_left_press_right])
                    .with_menu_nav(MenuNav::ChoiceMenu)
                    .with_back_on_first_page()
                    .with_confirm_btn(Some(ButtonDetails::ghost())),
            ),
            Screen::Remember => framed(
                Some(TR::tutorial__title_remember),
                text(&[TR::tutorial__scroll_up])
                    .with_menu_nav(MenuNav::ChoiceMenu)
                    .with_back_on_first_page()
                    .with_confirm_btn(Some(button_text(TR::buttons__continue))),
            ),
            Screen::MenuIntro => framed(
                Some(TR::tutorial__title_handy_menu),
                text(&[TR::tutorial__menu, TR::tutorial__press_left])
                    .with_menu_nav(MenuNav::ChoiceMenu)
                    .with_back_on_first_page()
                    .with_confirm_btn(None),
            ),
            Screen::Menu => {
                let labels = Vec::from_iter([
                    TR::tutorial__complete.into(),
                    TR::tutorial__restart_tutorial.into(),
                ]);
                let danger_items = Vec::from_iter([false, false]);
                return Content::Menu(SimpleChoice::menu(labels, danger_items, 0));
            }
            Screen::Complete => framed(
                Some(TR::tutorial__title_tutorial_complete),
                text(&[TR::tutorial__ready_to_use])
                    .with_cancel_btn(Some(button_text(TR::buttons__again)))
                    .with_confirm_btn(Some(button_text(TR::buttons__continue))),
            ),
            Screen::MenuInfo => framed(
                Some(TR::tutorial__title_handy_menu),
                text(&[TR::tutorial__menu_later])
                    .with_menu_nav(MenuNav::Close)
                    .with_confirm_btn(None),
            ),
        };
        Content::Page(page)
    }
}

/// Paragraphs vertically centered on the screen.
fn text(texts: &[TR]) -> ButtonPage<FormattedText> {
    let mut ops = OpTextLayout::new(theme::TEXT_NORMAL);
    for (i, &text) in texts.iter().enumerate() {
        if i > 0 {
            ops.add_newline();
        }
        ops.add_text_with_font(text, fonts::FONT_NORMAL);
    }
    ButtonPage::new(FormattedText::new(ops).vertically_centered(), theme::BG)
}

fn framed(title: Option<TR>, page: ButtonPage<FormattedText>) -> TutorialPage {
    let frame = ScrollableFrame::new(page);
    match title {
        Some(title) => frame.with_title(title.into()),
        None => frame,
    }
}

fn button_text(text: TR) -> ButtonDetails {
    ButtonDetails::text(TString::from(text))
}

impl Component for Tutorial {
    type Msg = CancelConfirmMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bounds = bounds;
        self.pad.place(bounds);
        match &mut self.content {
            Content::Page(page) => page.place(bounds),
            Content::Menu(menu) => menu.place(bounds),
        };
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let hint = if matches!(self.screen, Screen::MiddleButton { .. }) {
            self.single_press.event(event)
        } else {
            None
        };

        let msg = match &mut self.content {
            Content::Page(page) => page.event(ctx, event).map(ContentMsg::Page),
            Content::Menu(menu) => menu.event(ctx, event).map(ContentMsg::Menu),
        };
        let next = match msg {
            Some(msg) => match self.next(msg) {
                Ok(next) => next,
                Err(result) => return Some(result),
            },
            None => hint.map(|hint| Screen::MiddleButton { hint: Some(hint) }),
        };
        if let Some(next) = next {
            self.go_to(ctx, next);
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.pad.render(target);
        match &self.content {
            Content::Page(page) => page.render(target),
            Content::Menu(menu) => menu.render(target),
        }
    }
}

/// Detecting a button pressed and released without the other one, for the
/// hint on `Screen::MiddleButton`.
#[derive(Default)]
struct SinglePress {
    /// How many buttons are down
    down: u8,
    /// Whether both buttons were down since all of them were released
    both: bool,
}

impl SinglePress {
    /// The button released after it was pressed alone.
    fn event(&mut self, event: Event) -> Option<ButtonPos> {
        match event {
            Event::Attach(_) => *self = Self::default(),
            Event::Button(ButtonEvent::ButtonPressed(
                PhysicalButton::Left | PhysicalButton::Right,
            )) => {
                self.down += 1;
                self.both |= self.down > 1;
            }
            // A button pressed before the screen was shown is not counted
            Event::Button(ButtonEvent::ButtonReleased(
                button @ (PhysicalButton::Left | PhysicalButton::Right),
            )) if self.down > 0 => {
                self.down -= 1;
                if self.down == 0 {
                    let alone = !self.both;
                    self.both = false;
                    if alone {
                        return Some(button.into());
                    }
                }
            }
            _ => {}
        }
        None
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Tutorial {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        // Traced as the current screen, like a standalone layout
        match &self.content {
            Content::Page(page) => page.trace(t),
            Content::Menu(menu) => menu.trace(t),
        }
    }
}
