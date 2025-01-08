use crate::ui::{
    component::{Component, Event, EventCtx},
    geometry::{Alignment2D, Offset, Rect},
    shape::{self, Renderer},
    util::Pager,
};

use super::{
    button::{Button, ButtonContent, ButtonMsg},
    theme, ButtonStyleSheet,
};

/// Component for control buttons in the bottom of the screen.
pub struct ActionBar {
    /// Behavior based on `Mode`
    mode: Mode,
    /// Right or single button, can have text or icon
    right_button: Button,
    /// Optional left button, can be shorter than the right one
    left_button: Option<Button>,
    area: Rect,
    /// Whether the left button is short
    left_short: bool,
    // TODO: review cloning() of those fields
    // Storage of original button content for paginated component
    left_original: Option<(ButtonContent, ButtonStyleSheet)>,
    right_original: Option<(ButtonContent, ButtonStyleSheet)>,
    // TODO: animation
}

pub enum ActionBarMsg {
    /// Cancel the action
    Cancelled,
    /// Go back to the previous screen of paginated component
    Prev,
    /// Go forward to the next screen of paginated component
    Next,
    /// Confirm the action
    Confirmed,
}

/// Describes the behavior of the action bar
enum Mode {
    /// Single confirm button taking full width
    Single,
    /// Cancel and confirm button; Up/Down navigation for paginated content
    Double { pager: Pager },
}

impl ActionBar {
    pub const ACTION_BAR_HEIGHT: i16 = 90; // [px]
    const SPACER_WIDTH: i16 = 4; // [px]
    const LEFT_SMALL_BUTTON_WIDTH: i16 = 120; // [px]
    /// TODO: use this offset
    /// offset for button content to move it towards center
    const BUTTON_CONTENT_OFFSET: Offset = Offset::x(12); // [px]

    const PAGINATE_LEFT_CONTENT: ButtonContent = ButtonContent::Icon(theme::ICON_CHEVRON_UP);
    const PAGINATE_RIGHT_CONTENT: ButtonContent = ButtonContent::Icon(theme::ICON_CHEVRON_DOWN);
    const PAGINATE_STYLESHEET: &'static ButtonStyleSheet = &theme::button_default();

    /// Create action bar with single button confirming the layout
    pub fn new_single(button: Button) -> Self {
        Self::new(Mode::Single, None, button)
    }

    /// Create action bar with cancel and confirm buttons. The component
    /// automatically shows navigation up/down buttons for paginated
    /// content.
    pub fn new_double(left: Button, right: Button) -> Self {
        Self::new(
            Mode::Double {
                pager: Pager::single_page(),
            },
            Some(left),
            right,
        )
    }

    pub fn with_left_short(mut self, left_short: bool) -> Self {
        self.left_short = left_short;
        self
    }

    pub fn update(&mut self, new_pager: Pager) {
        match &mut self.mode {
            Mode::Double { pager } => {
                *pager = new_pager;
                // Update left button - show original content/style only on first page
                if let Some(btn) = &mut self.left_button {
                    if pager.is_first() {
                        let (content, style) = unwrap!(self.left_original.clone());
                        btn.set_content(content);
                        btn.set_stylesheet(style);
                    } else {
                        btn.set_content(Self::PAGINATE_LEFT_CONTENT);
                        btn.set_stylesheet(*Self::PAGINATE_STYLESHEET);
                    }
                }

                // Update right button - show original content/style only on last page
                if pager.is_last() {
                    let (content, style) = unwrap!(self.right_original.clone());
                    self.right_button.set_content(content);
                    self.right_button.set_stylesheet(style);
                } else {
                    self.right_button.set_content(Self::PAGINATE_RIGHT_CONTENT);
                    self.right_button.set_stylesheet(*Self::PAGINATE_STYLESHEET);
                }
            }
            _ => {}
        }
    }

    // TODO: changing the left button to short/equal on paginated last page?
    // TODO: single button which is disabled for "Continue in the app" screen

    fn new(mode: Mode, left_button: Option<Button>, right_button: Button) -> Self {
        let (left_original, right_original) = match mode {
            Mode::Double { .. } => (
                left_button
                    .as_ref()
                    .map(|b| (b.content().clone(), b.style_sheet().clone())),
                Some((
                    right_button.content().clone(),
                    right_button.style_sheet().clone(),
                )),
            ),
            _ => (None, None),
        };

        Self {
            mode,
            right_button,
            left_button,
            area: Rect::zero(),
            left_short: false,
            left_original,
            right_original,
        }
    }
}

impl Component for ActionBar {
    type Msg = ActionBarMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        debug_assert_eq!(bounds.height(), Self::ACTION_BAR_HEIGHT);

        match &self.mode {
            Mode::Single => {
                self.right_button.place(bounds);
            }
            Mode::Double { .. } => {
                let (left, right) = if self.left_short {
                    let (left, rest) = bounds.split_left(Self::LEFT_SMALL_BUTTON_WIDTH);
                    let (_, right) = rest.split_left(Self::SPACER_WIDTH);
                    (left, right)
                } else {
                    let (left, _spacer, right) = bounds.split_center(Self::SPACER_WIDTH);
                    (left, right)
                };
                if let Some(btn) = &mut self.left_button {
                    btn.place(left);
                }
                self.right_button.place(right);
            }
        }

        self.area = bounds;
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match &self.mode {
            Mode::Single => {
                // Only handle confirm button
                if let Some(ButtonMsg::Clicked) = self.right_button.event(ctx, event) {
                    return Some(ActionBarMsg::Confirmed);
                }
            }
            Mode::Double { pager } => {
                if pager.is_single() {
                    // Single page - show back and confirm
                    if let Some(btn) = &mut self.left_button {
                        if let Some(ButtonMsg::Clicked) = btn.event(ctx, event) {
                            return Some(ActionBarMsg::Cancelled);
                        }
                    }
                    if let Some(msg) = self.right_button.event(ctx, event) {
                        match (&self.right_button.is_long_press(), msg) {
                            (true, ButtonMsg::LongPressed) | (false, ButtonMsg::Clicked) => {
                                return Some(ActionBarMsg::Confirmed);
                            }
                            _ => {}
                        }
                    }
                } else if pager.is_first() && !pager.is_single() {
                    // First page of multiple - go back and next page
                    if let Some(btn) = &mut self.left_button {
                        if let Some(ButtonMsg::Clicked) = btn.event(ctx, event) {
                            return Some(ActionBarMsg::Cancelled);
                        }
                    }
                    if let Some(ButtonMsg::Clicked) = self.right_button.event(ctx, event) {
                        return Some(ActionBarMsg::Next);
                    }
                } else if pager.is_last() && !pager.is_single() {
                    // Last page - enable up button, show confirm
                    if let Some(btn) = &mut self.left_button {
                        if let Some(ButtonMsg::Clicked) = btn.event(ctx, event) {
                            return Some(ActionBarMsg::Prev);
                        }
                    }
                    if let Some(msg) = self.right_button.event(ctx, event) {
                        match (&self.right_button.is_long_press(), msg) {
                            (true, ButtonMsg::LongPressed) | (false, ButtonMsg::Clicked) => {
                                return Some(ActionBarMsg::Confirmed);
                            }
                            _ => {}
                        }
                    }
                } else {
                    // Middle pages - navigations up/down
                    if let Some(btn) = &mut self.left_button {
                        if let Some(ButtonMsg::Clicked) = btn.event(ctx, event) {
                            return Some(ActionBarMsg::Prev);
                        }
                    }
                    if let Some(ButtonMsg::Clicked) = self.right_button.event(ctx, event) {
                        return Some(ActionBarMsg::Next);
                    }
                }
            }
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if let Some(btn) = &self.left_button {
            let pos_divider = btn.area().right_center();
            shape::ToifImage::new(pos_divider, theme::ICON_DASH_VERTICAL.toif)
                .with_align(Alignment2D::CENTER_LEFT)
                .with_fg(theme::GREY_EXTRA_DARK)
                .render(target);
            btn.render(target);
        }
        self.right_button.render(target);
    }
}
#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for ActionBar {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ActionBar");
        if let Some(btn) = &self.left_button {
            t.child("left_button", btn);
        }
        t.child("right_button", &self.right_button);
    }
}
