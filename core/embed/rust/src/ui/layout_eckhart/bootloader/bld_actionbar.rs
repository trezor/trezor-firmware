use crate::ui::{
    component::{Component, Event, EventCtx},
    geometry::{Alignment2D, Insets, Offset, Rect},
    shape::{self, Renderer},
};

use super::super::{
    component::{Button, ButtonMsg},
    theme::{self, Gradient},
};

/// Component for control buttons in the bottom of the screen. Reduced variant
/// for Bootloader UI.
pub struct BldActionBar {
    /// Behavior based on `Mode`
    mode: Mode,
    /// Right or single button.
    right_button: Button,
    /// Optional left button.
    left_button: Option<Button>,
    /// Whether to show divider between buttons
    show_divider: bool,
    area: Rect,
}

pub enum BldActionBarMsg {
    /// Cancel the action
    Cancelled,
    /// Confirm the action
    Confirmed,
}

/// Describes the behavior of the action bar
enum Mode {
    /// Single confirm button taking full width
    Single,
    /// Cancel and confirm button
    Double,
}

impl BldActionBar {
    pub const ACTION_BAR_HEIGHT: i16 = theme::ACTION_BAR_HEIGHT; // [px]
    const SPACER_WIDTH: i16 = 4; // [px]
    const BUTTON_CONTENT_OFFSET: Offset = Offset::x(12); // [px]
    const BUTTON_EXPAND_TOUCH: Insets = Insets::top(Self::ACTION_BAR_HEIGHT);

    /// Create action bar with single button confirming the layout.
    pub fn new_single(button: Button) -> Self {
        Self::new(
            Mode::Single,
            None,
            button
                .with_expanded_touch_area(Self::BUTTON_EXPAND_TOUCH)
                .with_gradient(Gradient::DefaultGrey),
        )
    }

    /// Create action bar with cancel and confirm buttons.
    pub fn new_double(left: Button, right: Button) -> Self {
        Self::new(
            Mode::Double,
            Some(
                left.with_expanded_touch_area(Self::BUTTON_EXPAND_TOUCH)
                    .with_content_offset(Self::BUTTON_CONTENT_OFFSET),
            ),
            right
                .with_expanded_touch_area(Self::BUTTON_EXPAND_TOUCH)
                .with_content_offset(Self::BUTTON_CONTENT_OFFSET.neg()),
        )
    }

    pub fn with_divider(mut self) -> Self {
        self.show_divider = true;
        self
    }

    fn new(mode: Mode, left_button: Option<Button>, right_button: Button) -> Self {
        Self {
            mode,
            right_button,
            left_button,
            show_divider: false,
            area: Rect::zero(),
        }
    }
}

impl Component for BldActionBar {
    type Msg = BldActionBarMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        debug_assert_eq!(bounds.height(), Self::ACTION_BAR_HEIGHT);

        match &self.mode {
            Mode::Single => {
                self.right_button.place(bounds);
            }
            Mode::Double => {
                let (left, _spacer, right) = bounds.split_center(Self::SPACER_WIDTH);
                self.left_button.place(left);
                self.right_button.place(right);
            }
        }

        self.area = bounds;
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match &self.mode {
            Mode::Single => {
                if let Some(ButtonMsg::Clicked) = self.right_button.event(ctx, event) {
                    return Some(BldActionBarMsg::Confirmed);
                }
            }
            Mode::Double => {
                if let Some(ButtonMsg::Clicked) = self.left_button.event(ctx, event) {
                    return Some(BldActionBarMsg::Cancelled);
                }
                if let Some(ButtonMsg::Clicked) = self.right_button.event(ctx, event) {
                    return Some(BldActionBarMsg::Confirmed);
                }
            }
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.left_button.render(target);
        self.right_button.render(target);
        if self.show_divider {
            shape::ToifImage::new(self.area.center(), theme::ICON_DASH_VERTICAL.toif)
                .with_align(Alignment2D::CENTER)
                .with_fg(theme::GREY_EXTRA_DARK)
                .render(target);
        }
    }
}
