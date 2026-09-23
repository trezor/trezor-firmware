use super::{theme, Button, ButtonMsg};
use crate::ui::component::{Component, Event, EventCtx};
use crate::ui::geometry::{Insets, Rect};
use crate::ui::shape::Renderer;
use crate::ui::util::Pager;

/// Component for control buttons at the bottom of the screen.
pub struct ActionBar {
    /// Behavior based on `Mode`
    mode: Mode,
    /// Left button
    left_button: Button,
    /// Right button
    right_button: Button,
}

pub enum ActionBarMsg {
    /// Go back to the previous page of the paginated content
    Prev,
    /// Go forward to the next page of the paginated content
    Next,
}

/// Describes the behavior of the action bar
#[derive(PartialEq)]
enum Mode {
    /// Only show pagination buttons, no confirm or cancel
    PaginateOnly,
}

impl ActionBar {
    /// Total height of the action bar, including the gaps above and below
    /// the buttons [px]
    pub const ACTION_BAR_HEIGHT: i16 = Self::BUTTON_HEIGHT + 2 * Self::BAR_GAP;
    /// Height of the buttons [px]
    const BUTTON_HEIGHT: i16 = 36;
    /// Gap between the buttons [px]
    const BUTTON_GAP: i16 = 8;
    /// Gap between the buttons and the edges of the screen [px]
    const BAR_GAP: i16 = 2;
    /// Corner radius of the buttons [px]
    const BUTTON_RADIUS: u8 = 2;
    /// Expand the touch area of the buttons towards the content
    const BUTTON_EXPAND_TOUCH: Insets = Insets::top(Self::ACTION_BAR_HEIGHT / 2);

    /// Create action bar with only pagination buttons. The component in this
    /// mode can only return `ActionBarMsg::Prev` and `ActionBarMsg::Next`
    /// messages. Both buttons are visible at all times, the one that would
    /// go out of range of the pager is disabled.
    pub fn new_paginate_only() -> Self {
        Self {
            mode: Mode::PaginateOnly,
            // Paginated content always starts on the first page, so the
            // "previous" button starts out disabled.
            left_button: Button::with_icon(theme::ICON_CHEVRON_UP)
                .styled(theme::button_actionbar())
                .with_radius(Self::BUTTON_RADIUS)
                .with_expanded_touch_area(Self::BUTTON_EXPAND_TOUCH)
                .initially_enabled(false),
            right_button: Button::with_icon(theme::ICON_CHEVRON_DOWN)
                .styled(theme::button_actionbar())
                .with_radius(Self::BUTTON_RADIUS)
                .with_expanded_touch_area(Self::BUTTON_EXPAND_TOUCH),
        }
    }

    /// Updates the pager of the component, enabling/disabling the navigation
    /// buttons according to the current page.
    pub fn update(&mut self, ctx: &mut EventCtx, new_pager: Pager) {
        self.left_button.enable_if(ctx, new_pager.has_prev());
        self.right_button.enable_if(ctx, new_pager.has_next());
    }
}

impl Component for ActionBar {
    type Msg = ActionBarMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        debug_assert_eq!(bounds.height(), Self::ACTION_BAR_HEIGHT);
        let bar_area = bounds.inset(Insets::uniform(Self::BAR_GAP));
        match &self.mode {
            Mode::PaginateOnly => {
                // Equal-sized `left_button` and `right_button`
                let (left_area, _, right_area) = bar_area.split_center(Self::BUTTON_GAP);
                self.left_button.place(left_area);
                self.right_button.place(right_area);
            }
        }
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match &self.mode {
            Mode::PaginateOnly => {
                // Only handle navigation, no confirm/cancel
                if let Some(ButtonMsg::Clicked) = self.left_button.event(ctx, event) {
                    return Some(ActionBarMsg::Prev);
                }
                if let Some(ButtonMsg::Clicked) = self.right_button.event(ctx, event) {
                    return Some(ActionBarMsg::Next);
                }
            }
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.left_button.render(target);
        self.right_button.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for ActionBar {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ActionBar");
        t.child("left_button", &self.left_button);
        t.child("right_button", &self.right_button);
    }
}
