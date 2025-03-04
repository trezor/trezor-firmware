use crate::{
    translations::TR,
    ui::{
        component::{Component, Event, EventCtx, Timeout},
        geometry::{Alignment2D, Insets, Offset, Rect},
        shape::{self, Renderer},
        util::{animation_disabled, Pager},
    },
};

use super::{
    super::component::{Button, ButtonContent, ButtonMsg, ButtonStyleSheet},
    theme, HoldToConfirmAnim,
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
    /// Whether the left button is short (default: true)
    left_short: bool,
    // Storage of original button content for paginated component
    left_original: Option<(ButtonContent, ButtonStyleSheet)>,
    right_original: Option<(ButtonContent, ButtonStyleSheet)>,
    /// Hold to confirm animation
    htc_anim: Option<HoldToConfirmAnim>,
    /// Timeout
    timeout: Option<Timeout>,
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
    /// Automatic confirmation after a timeout
    Timeout,
}

impl ActionBar {
    pub const ACTION_BAR_HEIGHT: i16 = 90; // [px]
    const SPACER_WIDTH: i16 = 4; // [px]
    const LEFT_SMALL_BUTTON_WIDTH: i16 = 120; // [px]
    /// offset for button content to move it towards center
    const BUTTON_CONTENT_OFFSET: Offset = Offset::x(12); // [px]
    const BUTTON_EXPAND_TOUCH: Insets = Insets::top(Self::ACTION_BAR_HEIGHT);

    const PAGINATE_LEFT_CONTENT: ButtonContent = ButtonContent::Icon(theme::ICON_CHEVRON_UP);
    const PAGINATE_RIGHT_CONTENT: ButtonContent = ButtonContent::Icon(theme::ICON_CHEVRON_DOWN);
    const PAGINATE_STYLESHEET: &'static ButtonStyleSheet = &theme::button_default();

    /// Create action bar with single button confirming the layout
    pub fn new_single(button: Button) -> Self {
        Self::new(
            Mode::Single,
            None,
            button.with_expanded_touch_area(Self::BUTTON_EXPAND_TOUCH),
            None,
        )
    }

    /// Create action bar with single button confirming the layout
    pub fn new_timeout(button: Button, timeout_ms: u32) -> Self {
        Self::new(
            Mode::Timeout,
            None,
            button
                .initially_enabled(false),
            Some(Timeout::new(timeout_ms)),
        )
    }

    /// Create action bar with cancel and confirm buttons. The component
    /// automatically shows navigation up/down buttons for paginated
    /// content.
    pub fn new_double(left: Button, right: Button) -> Self {
        Self::new(
            Mode::Double {
                pager: Pager::single_page(),
            },
            Some(
                left.with_expanded_touch_area(Self::BUTTON_EXPAND_TOUCH)
                    .with_content_offset(Self::BUTTON_CONTENT_OFFSET),
            ),
            right
                .with_expanded_touch_area(Self::BUTTON_EXPAND_TOUCH)
                .with_content_offset(Self::BUTTON_CONTENT_OFFSET.neg()),
            None,
        )
    }

    pub fn with_left_short(mut self, left_short: bool) -> Self {
        self.left_short = left_short;
        self
    }

    pub fn set_touch_expansion(&mut self, expand: Insets) {
        if let Some(btn) = &mut self.left_button {
            btn.set_expanded_touch_area(expand);
        }
        self.right_button.set_expanded_touch_area(expand);
    }

    pub fn update(&mut self, new_pager: Pager) {
        // TODO: review `clone()` of `left_content`/`right_content`
        match &mut self.mode {
            Mode::Double { pager } => {
                let old_is_last = pager.is_last();
                let new_is_last = new_pager.is_last();
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

                // If we're entering or leaving the last page and left_short is true,
                // we need to update the button placement
                if self.left_short && (old_is_last != new_is_last) {
                    self.place_buttons(self.area);
                }
            }
            _ => {}
        }
    }

    fn new(
        mode: Mode,
        left_button: Option<Button>,
        right_button: Button,
        timeout: Option<Timeout>,
    ) -> Self {
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

        let htc_anim = right_button
            .long_press()
            .filter(|_| !animation_disabled())
            .map(|dur| {
                HoldToConfirmAnim::new()
                    .with_duration(dur)
                    .with_header_overlay(TR::instructions__continue_holding.into())
            });

        Self {
            mode,
            right_button,
            left_button,
            area: Rect::zero(),
            left_short: true,
            left_original,
            right_original,
            htc_anim,
            timeout,
        }
    }

    /// Handle event of the right button at the last page, this includes:
    ///     - Single button mode
    ///     - Double button mode at single page component
    ///     - Double button mode at last page of paginated component
    /// The function takes care about triggering the correct action to
    /// HoldToConfirm or returning the correct message out of the ActionBar.
    fn event_right_button_at_last_page(
        &mut self,
        ctx: &mut EventCtx,
        msg: ButtonMsg,
    ) -> Option<ActionBarMsg> {
        let is_hold = self.right_button.long_press().is_some();
        match (msg, is_hold) {
            (ButtonMsg::Pressed, true) => {
                if let Some(htc_anim) = &mut self.htc_anim {
                    htc_anim.start();
                    ctx.request_anim_frame();
                    ctx.request_paint();
                    ctx.disable_swipe();
                }
            }
            (ButtonMsg::Clicked, true) => {
                if let Some(htc_anim) = &mut self.htc_anim {
                    htc_anim.stop();
                    ctx.request_anim_frame();
                    ctx.request_paint();
                    ctx.enable_swipe();
                } else {
                    // Animations disabled, return confirmed
                    return Some(ActionBarMsg::Confirmed);
                }
            }
            (ButtonMsg::Released, true) => {
                if let Some(htc_anim) = &mut self.htc_anim {
                    htc_anim.stop();
                    ctx.request_anim_frame();
                    ctx.request_paint();
                    ctx.enable_swipe();
                }
            }
            (ButtonMsg::Clicked, false) | (ButtonMsg::LongPressed, true) => {
                return Some(ActionBarMsg::Confirmed);
            }
            _ => {}
        }
        None
    }

    fn place_buttons(&mut self, bounds: Rect) {
        match &self.mode {
            Mode::Single | Mode::Timeout => {
                self.right_button.place(bounds);
            }
            Mode::Double { pager } => {
                let (left_area, right_area) = if self.left_short && pager.is_last() {
                    // Small left button when on last page
                    let (left, rest) = bounds.split_left(Self::LEFT_SMALL_BUTTON_WIDTH);
                    let (_, right) = rest.split_left(Self::SPACER_WIDTH);
                    (left, right)
                } else {
                    // Standard equal-sized buttons
                    let (left, _, right) = bounds.split_center(Self::SPACER_WIDTH);
                    (left, right)
                };
                self.left_button.place(left_area);
                self.right_button.place(right_area);
            }
        }
    }
}

impl Component for ActionBar {
    type Msg = ActionBarMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        debug_assert_eq!(bounds.height(), Self::ACTION_BAR_HEIGHT);
        self.place_buttons(bounds);
        self.area = bounds;
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.htc_anim.event(ctx, event);
        match &self.mode {
            Mode::Timeout => {
                if self
                    .timeout
                    .as_mut()
                    .and_then(|t| t.event(ctx, event))
                    .is_some()
                {
                    return Some(ActionBarMsg::Confirmed);
                }
            }
            Mode::Single => {
                // Only handle confirm button
                if let Some(msg) = self.right_button.event(ctx, event) {
                    return self.event_right_button_at_last_page(ctx, msg);
                }
            }
            Mode::Double { pager } => {
                if pager.is_single() {
                    // Single page - show back and confirm
                    if let Some(ButtonMsg::Clicked) = self.left_button.event(ctx, event) {
                        return Some(ActionBarMsg::Cancelled);
                    }
                    if let Some(msg) = self.right_button.event(ctx, event) {
                        return self.event_right_button_at_last_page(ctx, msg);
                    }
                } else if pager.is_first() && !pager.is_single() {
                    // First page of multiple - go back and next page
                    if let Some(ButtonMsg::Clicked) = self.left_button.event(ctx, event) {
                        return Some(ActionBarMsg::Cancelled);
                    }
                    if let Some(ButtonMsg::Clicked) = self.right_button.event(ctx, event) {
                        return Some(ActionBarMsg::Next);
                    }
                } else if pager.is_last() && !pager.is_single() {
                    // Last page - enable up button, show confirm
                    if let Some(ButtonMsg::Clicked) = self.left_button.event(ctx, event) {
                        return Some(ActionBarMsg::Prev);
                    }
                    if let Some(msg) = self.right_button.event(ctx, event) {
                        return self.event_right_button_at_last_page(ctx, msg);
                    }
                } else {
                    // Middle pages - navigations up/down
                    if let Some(ButtonMsg::Clicked) = self.left_button.event(ctx, event) {
                        return Some(ActionBarMsg::Prev);
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
        if let Some(htc_anim) = &self.htc_anim {
            htc_anim.render(target);
        }
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
