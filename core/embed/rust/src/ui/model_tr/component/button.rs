use crate::ui::{
    component::{Component, Event, EventCtx},
    display::{self, Color, Font},
    event::{ButtonEvent, PhysicalButton},
    geometry::{Offset, Point, Rect},
};

use super::theme;

pub enum ButtonMsg {
    Clicked,
}

#[derive(Copy, Clone)]
pub enum ButtonPos {
    Left,
    Middle,
    Right,
}

impl ButtonPos {
    fn hit(&self, b: &PhysicalButton) -> bool {
        matches!(
            (self, b),
            (Self::Left, PhysicalButton::Left)
                | (Self::Middle, PhysicalButton::Middle)
                | (Self::Right, PhysicalButton::Right)
        )
    }
}

pub struct Button<T> {
    area: Rect,
    pos: ButtonPos,
    baseline: Point,
    content: ButtonContent<T>,
    styles: ButtonStyleSheet,
    state: State,
}

impl<T: AsRef<str>> Button<T> {
    pub fn new(pos: ButtonPos, content: ButtonContent<T>, styles: ButtonStyleSheet) -> Self {
        Self {
            pos,
            content,
            styles,
            baseline: Point::zero(),
            area: Rect::zero(),
            state: State::Released,
        }
    }

    pub fn with_text(pos: ButtonPos, text: T, styles: ButtonStyleSheet) -> Self {
        Self::new(pos, ButtonContent::Text(text), styles)
    }

    pub fn with_icon(pos: ButtonPos, image: &'static [u8], styles: ButtonStyleSheet) -> Self {
        Self::new(pos, ButtonContent::Icon(image), styles)
    }

    pub fn content(&self) -> &ButtonContent<T> {
        &self.content
    }

    fn style(&self) -> &ButtonStyle {
        match self.state {
            State::Released => self.styles.normal,
            State::Pressed => self.styles.active,
        }
    }

    fn set(&mut self, ctx: &mut EventCtx, state: State) {
        if self.state != state {
            self.state = state;
            ctx.request_paint();
        }
    }

    pub fn set_released(&mut self, ctx: &mut EventCtx) {
        self.set(ctx, State::Released);
    }

    fn placement(
        area: Rect,
        pos: ButtonPos,
        content: &ButtonContent<T>,
        styles: &ButtonStyleSheet,
    ) -> (Rect, Point) {
        let border_width = if styles.normal.border_horiz { 2 } else { 0 };
        let content_width = match content {
            ButtonContent::Text(text) => styles.normal.font.text_width(text.as_ref()) - 1,
            ButtonContent::Icon(_icon) => todo!(),
        };
        let button_width = content_width + 2 * border_width;
        let area = match pos {
            ButtonPos::Left => area.split_left(button_width).0,
            ButtonPos::Right => area.split_right(button_width).1,
            ButtonPos::Middle => area.split_center(button_width),
        };

        let start_of_baseline = area.bottom_left() + Offset::new(border_width, -2);

        return (area, start_of_baseline);
    }
}

impl<T> Component for Button<T>
where
    T: AsRef<str>,
{
    type Msg = ButtonMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (area, baseline) = Self::placement(bounds, self.pos, &self.content, &self.styles);
        self.area = area;
        self.baseline = baseline;
        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match event {
            Event::Button(ButtonEvent::ButtonPressed(which)) if self.pos.hit(&which) => {
                self.set(ctx, State::Pressed);
            }
            Event::Button(ButtonEvent::ButtonReleased(which)) if self.pos.hit(&which) => {
                if matches!(self.state, State::Pressed) {
                    self.set(ctx, State::Released);
                    return Some(ButtonMsg::Clicked);
                }
            }
            _ => {}
        };
        None
    }

    fn paint(&mut self) {
        let style = self.style();

        match &self.content {
            ButtonContent::Text(text) => {
                let background_color = style.text_color.neg();
                if style.border_horiz {
                    display::rect_fill_rounded1(self.area, background_color, theme::BG);
                } else {
                    display::rect_fill(self.area, background_color)
                }

                display::text(
                    self.baseline,
                    text.as_ref(),
                    style.font,
                    style.text_color,
                    background_color,
                );
            }
            ButtonContent::Icon(_image) => {
                todo!();
            }
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Button<T>
where
    T: AsRef<str> + crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Button");
        match &self.content {
            ButtonContent::Text(text) => t.field("text", text),
            ButtonContent::Icon(_) => t.symbol("icon"),
        }
        t.close();
    }
}

#[derive(PartialEq, Eq)]
enum State {
    Released,
    Pressed,
}

pub enum ButtonContent<T> {
    Text(T),
    Icon(&'static [u8]),
}

pub struct ButtonStyleSheet {
    pub normal: &'static ButtonStyle,
    pub active: &'static ButtonStyle,
}

pub struct ButtonStyle {
    pub font: Font,
    pub text_color: Color,
    pub border_horiz: bool,
}

/// Monitoring when to send double press events.
/// Aggregates individual left-and-right clicks and issues
/// a double-press (middle button press/release) when appropriate.
pub struct DoublePressHandler {
    left_pressed: bool,
    right_pressed: bool,
    wait_for_double_press_release: bool,
    send_double_press_pressed: bool,
    send_double_press_released: bool,
    /// In some situations we do not want to send individual events.
    /// For example when releasing the first button from double press,
    /// we do not want to send the release event for the button itself,
    /// as that could trigger a click on the single button.
    /// (Considering that first-to-release button was first-to-press.)
    do_not_send_any_event: bool,
}

impl DoublePressHandler {
    pub fn new() -> Self {
        Self {
            left_pressed: false,
            right_pressed: false,
            wait_for_double_press_release: false,
            send_double_press_pressed: false,
            send_double_press_released: false,
            do_not_send_any_event: false,
        }
    }

    /// Getting a possibly new event coming from double-press aggregation.
    /// It is even possible that event will be ignored
    /// (the release of the first button of the double-press will be ignored,
    /// not to cause any "normal" event to the button).
    pub fn possibly_replace_event(&mut self, event: Event) -> Option<Event> {
        match event {
            Event::Button(button_event) => {
                let new_button_event = self.handle_double_press(button_event)?;
                Some(Event::Button(new_button_event))
            }
            _ => Some(event),
        }
    }

    pub fn handle_double_press(&mut self, original_event: ButtonEvent) -> Option<ButtonEvent> {
        match original_event {
            ButtonEvent::ButtonPressed(PhysicalButton::Left) => {
                self.left_pressed = true;
                if self.right_pressed {
                    self.send_double_press_pressed = true;
                }
            }
            ButtonEvent::ButtonPressed(PhysicalButton::Right) => {
                self.right_pressed = true;
                if self.left_pressed {
                    self.send_double_press_pressed = true;
                }
            }
            ButtonEvent::ButtonReleased(PhysicalButton::Left) => {
                self.left_pressed = false;
                if self.right_pressed {
                    // not send release event for the button itself
                    self.do_not_send_any_event = true;
                } else {
                    self.do_not_send_any_event = false;
                    self.send_double_press_released = true;
                }
            }
            ButtonEvent::ButtonReleased(PhysicalButton::Right) => {
                self.right_pressed = false;
                if self.left_pressed {
                    // not send release event for the button itself
                    self.do_not_send_any_event = true;
                } else {
                    self.do_not_send_any_event = false;
                    self.send_double_press_released = true;
                }
            }
            // Middle button click will never come from the user
            _ => {}
        };

        // Deciding whether to send any event, and which
        // By default, sending the original event
        if self.do_not_send_any_event {
            None
        } else if self.send_double_press_pressed {
            self.send_double_press_pressed = false;
            self.wait_for_double_press_release = true;
            Some(ButtonEvent::ButtonPressed(PhysicalButton::Middle))
        } else if self.send_double_press_released && self.wait_for_double_press_release {
            self.send_double_press_released = false;
            self.wait_for_double_press_release = false;
            Some(ButtonEvent::ButtonReleased(PhysicalButton::Middle))
        } else {
            Some(original_event)
        }
    }

    /// Identify double press started, so we can take some action.
    pub fn is_event_double_press_pressed(&self, event: Event) -> bool {
        matches!(
            event,
            Event::Button(ButtonEvent::ButtonPressed(PhysicalButton::Middle))
        )
    }
}
