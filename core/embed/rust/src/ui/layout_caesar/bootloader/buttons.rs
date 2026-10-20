use super::super::theme::bootloader::{
    ARMED_ICON_WIDTH, ARMS_MARGIN, BLD_BG, BLD_FG, BUTTON_HEIGHT, BUTTON_ICON_WIDTH,
    BUTTON_OUTLINE, FONT_BUTTON, ICON_ARM_LEFT, ICON_ARM_RIGHT, ICON_ARROW_LEFT, ICON_ARROW_RIGHT,
    ICON_CLOSE, ICON_MENU, ICON_SELECT,
};
use crate::ui::component::{Component, Event, EventCtx, Pad};
use crate::ui::display::Icon;
use crate::ui::event::{ButtonEvent, PhysicalButton};
use crate::ui::geometry::{Alignment2D, Offset, Rect};
use crate::ui::shape::{self, Renderer};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ButtonPos {
    Left,
    /// Triggered by pressing both buttons
    Middle,
    Right,
}

impl ButtonPos {
    fn from_physical(button: PhysicalButton) -> Self {
        if button == PhysicalButton::Left {
            Self::Left
        } else {
            Self::Right
        }
    }
}

/// Content and decoration of a button, looking the same as the firmware
/// buttons.
#[derive(Copy, Clone)]
pub enum Button {
    /// Icon in the corner, moved by the offset
    Icon(Icon, Offset),
    /// Outlined text
    Text(&'static str),
    /// Text between arms
    ArmedText(&'static str),
    /// Icon between arms
    ArmedIcon(Icon),
}

impl Button {
    pub const fn cancel() -> Self {
        Self::Icon(ICON_CLOSE, Offset::new(3, -3))
    }

    /// Opening the context menu
    pub const fn menu() -> Self {
        Self::Icon(ICON_MENU, Offset::new(3, -3))
    }

    pub const fn left_arrow() -> Self {
        Self::Icon(ICON_ARROW_LEFT, Offset::new(4, -3))
    }

    pub const fn right_arrow() -> Self {
        Self::Icon(ICON_ARROW_RIGHT, Offset::new(-4, -3))
    }

    /// Entering the selected menu item
    pub const fn select() -> Self {
        Self::ArmedIcon(ICON_SELECT)
    }

    fn area(&self, pos: ButtonPos, bounds: Rect) -> Rect {
        // Arms connect to the center, therefore the height is smaller
        let (width, height) = match self {
            Self::Icon(..) => (BUTTON_ICON_WIDTH, BUTTON_HEIGHT),
            Self::Text(text) => (
                FONT_BUTTON.visible_text_width(text) + 2 * BUTTON_OUTLINE,
                BUTTON_HEIGHT,
            ),
            Self::ArmedText(text) => (
                FONT_BUTTON.visible_text_width(text) + 2 * ARMS_MARGIN,
                BUTTON_HEIGHT - 2,
            ),
            Self::ArmedIcon(_) => (ARMED_ICON_WIDTH, BUTTON_HEIGHT - 2),
        };
        let area = bounds.split_bottom(height).1;
        match pos {
            ButtonPos::Left => area.split_left(width).0,
            ButtonPos::Middle => area.split_center(width).1,
            ButtonPos::Right => area.split_right(width).1,
        }
    }

    fn render<'s>(
        &self,
        target: &mut impl Renderer<'s>,
        pos: ButtonPos,
        bounds: Rect,
        pressed: bool,
    ) {
        let area = self.area(pos, bounds);
        let (fg, bg) = if pressed {
            (BLD_BG, BLD_FG)
        } else {
            (BLD_FG, BLD_BG)
        };

        // Background: filled when pressed, outlined for text
        if pressed {
            shape::Bar::new(area)
                .with_radius(3)
                .with_bg(bg)
                .render(target);
        } else if let Self::Text(_) = self {
            shape::Bar::new(area)
                .with_radius(3)
                .with_fg(fg)
                .render(target);
        } else {
            shape::Bar::new(area).with_bg(bg).render(target);
        }

        // Arms are never inverted
        if let Self::ArmedText(_) | Self::ArmedIcon(_) = self {
            shape::ToifImage::new(area.left_center(), ICON_ARM_LEFT.toif)
                .with_align(Alignment2D::TOP_RIGHT)
                .with_fg(BLD_FG)
                .render(target);
            shape::ToifImage::new(area.right_center(), ICON_ARM_RIGHT.toif)
                .with_align(Alignment2D::TOP_LEFT)
                .with_fg(BLD_FG)
                .render(target);
        }

        match *self {
            Self::Icon(icon, offset) => {
                let icon_area = area.translate(offset);
                let (point, align) = match pos {
                    ButtonPos::Left => (icon_area.bottom_left(), Alignment2D::BOTTOM_LEFT),
                    ButtonPos::Middle => (icon_area.center(), Alignment2D::CENTER),
                    ButtonPos::Right => (icon_area.bottom_right(), Alignment2D::BOTTOM_RIGHT),
                };
                shape::ToifImage::new(point, icon.toif)
                    .with_align(align)
                    .with_fg(fg)
                    .render(target);
            }
            Self::ArmedIcon(icon) => {
                shape::ToifImage::new(area.center(), icon.toif)
                    .with_align(Alignment2D::CENTER)
                    .with_fg(fg)
                    .render(target);
            }
            Self::Text(text) | Self::ArmedText(text) => {
                let margin = if let Self::Text(_) = self {
                    BUTTON_OUTLINE
                } else {
                    ARMS_MARGIN
                };
                let baseline = area.bottom_left()
                    + Offset::new(margin - FONT_BUTTON.start_x_bearing(text), -margin);
                shape::Text::new(baseline, text, FONT_BUTTON)
                    .with_fg(fg)
                    .render(target);
            }
        }
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
enum State {
    Nothing,
    OneDown(PhysicalButton),
    /// Both buttons are down - the middle button
    BothDown,
    /// One button was released after both were down
    OneReleased(PhysicalButton),
}

/// Bottom bar with up to three buttons. A simplified copy of the firmware
/// `ButtonController` without hold-to-confirm, long press and "Shift", which
/// need timers.
pub struct Buttons {
    pad: Pad,
    left: Option<Button>,
    middle: Option<Button>,
    right: Option<Button>,
    state: State,
}

impl Buttons {
    pub fn new(left: Option<Button>, middle: Option<Button>, right: Option<Button>) -> Self {
        Self {
            pad: Pad::with_background(BLD_BG).with_clear(),
            left,
            middle,
            right,
            state: State::Nothing,
        }
    }

    pub fn set(&mut self, left: Option<Button>, middle: Option<Button>, right: Option<Button>) {
        self.left = left;
        self.middle = middle;
        self.right = right;
        self.pad.clear();
    }

    fn get(&self, pos: ButtonPos) -> Option<Button> {
        match pos {
            ButtonPos::Left => self.left,
            ButtonPos::Middle => self.middle,
            ButtonPos::Right => self.right,
        }
    }

    /// The button currently held down.
    pub fn pressed(&self) -> Option<ButtonPos> {
        match self.state {
            State::Nothing => None,
            State::OneDown(button) => Some(ButtonPos::from_physical(button)),
            State::BothDown | State::OneReleased(_) => Some(ButtonPos::Middle),
        }
    }
}

impl Component for Buttons {
    /// Triggered button, sent on release
    type Msg = ButtonPos;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.pad.place(bounds);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let (state, msg) = match (self.state, event) {
            // Presses that happened before the screen was shown are forgotten
            (_, Event::Attach(_)) => (State::Nothing, None),
            (State::Nothing, Event::Button(ButtonEvent::ButtonPressed(b)))
                if matches!(b, PhysicalButton::Left | PhysicalButton::Right) =>
            {
                (State::OneDown(b), None)
            }
            (State::OneDown(down), Event::Button(ButtonEvent::ButtonReleased(b))) if b == down => {
                let pos = ButtonPos::from_physical(b);
                (State::Nothing, self.get(pos).map(|_| pos))
            }
            (State::OneDown(down), Event::Button(ButtonEvent::ButtonPressed(b)))
                if b != down && self.middle.is_some() =>
            {
                (State::BothDown, None)
            }
            (State::BothDown, Event::Button(ButtonEvent::ButtonReleased(b))) => {
                (State::OneReleased(b), None)
            }
            (State::OneReleased(up), Event::Button(ButtonEvent::ButtonPressed(b))) if b == up => {
                (State::BothDown, None)
            }
            (State::OneReleased(up), Event::Button(ButtonEvent::ButtonReleased(b))) if b != up => {
                (State::Nothing, self.middle.map(|_| ButtonPos::Middle))
            }
            (state, _) => (state, None),
        };
        if state != self.state {
            self.state = state;
            ctx.request_paint();
        }
        msg
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.pad.render(target);
        let pressed = self.pressed();
        for pos in [ButtonPos::Left, ButtonPos::Middle, ButtonPos::Right] {
            if let Some(button) = self.get(pos) {
                button.render(target, pos, self.pad.area, pressed == Some(pos));
            }
        }
    }
}
