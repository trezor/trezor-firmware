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
    super::component::{Button, ButtonMsg},
    theme, HoldToConfirmAnim,
};

/// Component for control buttons in the bottom of the screen.
pub struct ActionBar {
    /// Behavior based on `Mode`
    mode: Mode,
    /// Right or single confirm button, can have text or icon
    right_button: Option<Button>,
    /// Left cancel button, can be shorter than the right one
    left_button: Option<Button>,
    /// Area of the action bar
    area: Rect,
    /// Hold to confirm animation
    htc_anim: Option<HoldToConfirmAnim>,
    /// Timeout
    timeout: Option<Timeout>,
    /// Pager for paginated content
    pager: Pager,
    /// Left button for paginated content
    prev_button: Button,
    /// Right button for paginated content
    next_button: Button,
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
#[derive(PartialEq)]
enum Mode {
    /// Single confirm button
    Single,
    /// Cancel and confirm button
    Double { left_short: bool },
    /// Automatic confirmation after a timeout
    Timeout,
    /// Only show pagination buttons, no confirm or cancel
    PaginateOnly,
}

impl ActionBar {
    pub const ACTION_BAR_HEIGHT: i16 = 90; // [px]
    const SPACER_WIDTH: i16 = 4; // [px]
    const LEFT_SMALL_BUTTON_WIDTH: i16 = 120; // [px]
    /// offset for button content to move it towards center
    const BUTTON_CONTENT_OFFSET: Offset = Offset::x(12); // [px]
    const BUTTON_EXPAND_TOUCH: Insets = Insets::top(Self::ACTION_BAR_HEIGHT);

    /// Create action bar with single button confirming the layout. The
    /// component automatically shows navigation up/down buttons for
    /// paginated content.
    pub fn new_single(button: Button) -> Self {
        Self::new(
            Mode::Single,
            None,
            Some(button.with_expanded_touch_area(Self::BUTTON_EXPAND_TOUCH)),
            None,
        )
    }

    /// Create action bar with single button confirming the layout
    pub fn new_timeout(button: Button, timeout_ms: u32) -> Self {
        Self::new(
            Mode::Timeout,
            None,
            Some(button.initially_enabled(false)),
            Some(Timeout::new(timeout_ms)),
        )
    }

    /// Create action bar with cancel and confirm buttons. The component
    /// automatically shows navigation up/down buttons for paginated
    /// content.
    pub fn new_double(left: Button, right: Button) -> Self {
        Self::new(
            Mode::Double { left_short: true },
            Some(
                left.with_expanded_touch_area(Self::BUTTON_EXPAND_TOUCH)
                    .with_content_offset(Self::BUTTON_CONTENT_OFFSET),
            ),
            Some(
                right
                    .with_expanded_touch_area(Self::BUTTON_EXPAND_TOUCH)
                    .with_content_offset(Self::BUTTON_CONTENT_OFFSET.neg()),
            ),
            None,
        )
    }

    pub fn new_cancel_confirm() -> Self {
        Self::new_double(
            Button::with_icon(theme::ICON_CROSS),
            Button::with_text(TR::buttons__confirm.into()),
        )
    }

    /// Create action bar with only pagination buttons. The component in this
    /// mode can only return `ActionBarMsg::Prev` and `ActionBarMsg::Next`
    /// messages.
    pub fn new_paginate_only() -> Self {
        Self::new(Mode::PaginateOnly, None, None, None)
    }

    pub fn with_left_short(mut self) -> Self {
        if let Mode::Double { ref mut left_short } = self.mode {
            *left_short = true;
        }
        self
    }

    pub fn set_touch_expansion(&mut self, expand: Insets) {
        if let Some(btn) = &mut self.left_button {
            btn.set_expanded_touch_area(expand);
        }
        if let Some(btn) = &mut self.right_button {
            btn.set_expanded_touch_area(expand);
        }
    }

    pub fn touch_area(&self) -> Rect {
        let right_area = self
            .right_button
            .as_ref()
            .map_or(Rect::zero(), |right| right.touch_area());
        self.left_button
            .as_ref()
            .map_or(right_area, |left| right_area.union(left.touch_area()))
    }

    /// Updates the pager of the component. This is used to show and process the
    /// navigation buttons.
    pub fn update(&mut self, new_pager: Pager) {
        let old_is_last = self.pager.is_last();
        let new_is_last = new_pager.is_last();
        let old_is_first = self.pager.is_first();
        let new_is_first = new_pager.is_first();

        self.pager = new_pager;
        if (old_is_last != new_is_last) || (new_is_first != old_is_first) {
            self.place_buttons(self.area);
        }
    }

    fn new(
        mode: Mode,
        left_button: Option<Button>,
        right_button: Option<Button>,
        timeout: Option<Timeout>,
    ) -> Self {
        let htc_anim = if let Some(ref right_button) = right_button {
            right_button
                .long_press()
                .filter(|_| !animation_disabled())
                .map(|dur| {
                    HoldToConfirmAnim::new()
                        .with_duration(dur)
                        .with_header_overlay(TR::instructions__continue_holding.into())
                })
        } else {
            None
        };

        Self {
            mode,
            right_button,
            left_button,
            area: Rect::zero(),
            htc_anim,
            timeout,
            pager: Pager::default(),
            prev_button: Button::with_icon(theme::ICON_CHEVRON_UP)
                .styled(theme::button_default())
                .with_expanded_touch_area(Self::BUTTON_EXPAND_TOUCH)
                .with_content_offset(Self::BUTTON_CONTENT_OFFSET),
            next_button: Button::with_icon(theme::ICON_CHEVRON_DOWN)
                .styled(theme::button_default())
                .with_expanded_touch_area(Self::BUTTON_EXPAND_TOUCH)
                .with_content_offset(Self::BUTTON_CONTENT_OFFSET.neg()),
        }
    }

    /// Handle event of the `right_button` at the last page.
    ///
    /// The function takes care about triggering the correct action to
    /// HoldToConfirm or returning the correct message out of the ActionBar.
    fn event_right_button(&mut self, ctx: &mut EventCtx, msg: ButtonMsg) -> Option<ActionBarMsg> {
        let is_hold = self
            .right_button
            .as_ref()
            .is_some_and(|btn| btn.long_press().is_some());
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
            Mode::Timeout => {
                self.right_button.place(bounds);
            }
            Mode::Single => {
                let (left_area, right_area) = if !self.pager.is_first() {
                    self.next_button
                        .set_content_offset(Self::BUTTON_CONTENT_OFFSET.neg());
                    // Small `prev_button` when not on first page
                    let (left, rest) = bounds.split_left(Self::LEFT_SMALL_BUTTON_WIDTH);
                    let (_, right) = rest.split_left(Self::SPACER_WIDTH);
                    (left, right)
                } else {
                    self.next_button.set_content_offset(Offset::zero());
                    (Rect::zero(), bounds)
                };
                self.right_button.place(right_area);
                self.prev_button.place(left_area);
                self.next_button.place(right_area);
            }
            Mode::Double { left_short } => {
                let (left_area, right_area) = if *left_short && self.pager.is_last() {
                    // Small left button
                    let (left, rest) = bounds.split_left(Self::LEFT_SMALL_BUTTON_WIDTH);
                    let (_, right) = rest.split_left(Self::SPACER_WIDTH);
                    (left, right)
                } else {
                    // Equal-sized buttons
                    let (left, _, right) = bounds.split_center(Self::SPACER_WIDTH);
                    (left, right)
                };
                self.left_button.place(left_area);
                self.right_button.place(right_area);
                self.prev_button.place(left_area);
                self.next_button.place(right_area);
            }
            Mode::PaginateOnly => {
                let (left_area, right_area) = if self.pager.is_first() {
                    // Only `next_button`
                    self.next_button.set_content_offset(Offset::zero());
                    (Rect::zero(), bounds)
                } else if self.pager.is_last() {
                    // Only `prev_button`
                    self.prev_button.set_content_offset(Offset::zero());
                    (bounds, Rect::zero())
                } else {
                    // Equal-sized `next_button` and `prev_button`
                    let (left, _, right) = bounds.split_center(Self::SPACER_WIDTH);
                    self.prev_button
                        .set_content_offset(Self::BUTTON_CONTENT_OFFSET);
                    self.next_button
                        .set_content_offset(Self::BUTTON_CONTENT_OFFSET.neg());
                    (left, right)
                };
                self.prev_button.place(left_area);
                self.next_button.place(right_area);
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
                if self.pager.is_single() {
                    // Only handle confirm button
                    if let Some(msg) = self.right_button.event(ctx, event) {
                        return self.event_right_button(ctx, msg);
                    }
                } else if self.pager.is_first() && !self.pager.is_single() {
                    // First page of multiple: next_button
                    if let Some(ButtonMsg::Clicked) = self.next_button.event(ctx, event) {
                        return Some(ActionBarMsg::Next);
                    }
                } else if !self.pager.is_last() && !self.pager.is_single() {
                    // Middle pages: prev_button and next_button
                    if let Some(ButtonMsg::Clicked) = self.prev_button.event(ctx, event) {
                        return Some(ActionBarMsg::Prev);
                    }
                    if let Some(ButtonMsg::Clicked) = self.next_button.event(ctx, event) {
                        return Some(ActionBarMsg::Next);
                    }
                } else {
                    // Last page: prev_button and right_button
                    if let Some(ButtonMsg::Clicked) = self.prev_button.event(ctx, event) {
                        return Some(ActionBarMsg::Prev);
                    }
                    if let Some(msg) = self.right_button.event(ctx, event) {
                        return self.event_right_button(ctx, msg);
                    }
                }
            }
            Mode::Double { .. } => {
                if self.pager.is_single() {
                    // Single page: left_button and right_button
                    if let Some(ButtonMsg::Clicked) = self.left_button.event(ctx, event) {
                        return Some(ActionBarMsg::Cancelled);
                    }
                    if let Some(msg) = self.right_button.event(ctx, event) {
                        return self.event_right_button(ctx, msg);
                    }
                } else if self.pager.is_first() && !self.pager.is_single() {
                    // First page of multiple: left_button and next_button
                    if let Some(ButtonMsg::Clicked) = self.left_button.event(ctx, event) {
                        return Some(ActionBarMsg::Cancelled);
                    }
                    if let Some(ButtonMsg::Clicked) = self.next_button.event(ctx, event) {
                        return Some(ActionBarMsg::Next);
                    }
                } else if !self.pager.is_last() && !self.pager.is_single() {
                    // Middle pages: prev_button and next_button
                    if let Some(ButtonMsg::Clicked) = self.prev_button.event(ctx, event) {
                        return Some(ActionBarMsg::Prev);
                    }
                    if let Some(ButtonMsg::Clicked) = self.next_button.event(ctx, event) {
                        return Some(ActionBarMsg::Next);
                    }
                } else {
                    // Last page: prev_button and right_button
                    if let Some(ButtonMsg::Clicked) = self.prev_button.event(ctx, event) {
                        return Some(ActionBarMsg::Prev);
                    }
                    if let Some(msg) = self.right_button.event(ctx, event) {
                        return self.event_right_button(ctx, msg);
                    }
                }
            }
            Mode::PaginateOnly => {
                // Only handle navigation, no confirm/cancel regardless of page
                if !self.pager.is_first() && !self.pager.is_single() {
                    if let Some(ButtonMsg::Clicked) = self.prev_button.event(ctx, event) {
                        return Some(ActionBarMsg::Prev);
                    }
                }
                if !self.pager.is_last() && !self.pager.is_single() {
                    if let Some(ButtonMsg::Clicked) = self.next_button.event(ctx, event) {
                        return Some(ActionBarMsg::Next);
                    }
                }
            }
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let show_divider = match self.mode {
            Mode::Single => !self.pager.is_first(),
            Mode::Double { .. } => true,
            Mode::Timeout => false,
            Mode::PaginateOnly => !self.pager.is_first() && !self.pager.is_last(),
        };
        if show_divider {
            let pos_divider = self.prev_button.area().right_center();
            shape::ToifImage::new(pos_divider, theme::ICON_DASH_VERTICAL.toif)
                .with_align(Alignment2D::CENTER_LEFT)
                .with_fg(theme::GREY_EXTRA_DARK)
                .render(target);
        }
        if self.pager.is_first() {
            self.left_button.render(target);
        } else {
            self.prev_button.render(target);
        }
        if self.pager.is_last() {
            self.right_button.render(target);
        } else {
            self.next_button.render(target);
        }
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
        if let Some(btn) = &self.right_button {
            t.child("right_button", btn);
        }
    }
}
