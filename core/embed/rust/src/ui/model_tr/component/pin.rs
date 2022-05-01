// Almost a copy of `page.rs` without the unnecessary stuff and with some extra
// logic.

use crate::ui::{
    component::{Component, Event, EventCtx, Pad},
    display,
    geometry::{Point, Rect},
};

use super::{theme, Button, ButtonMsg, ButtonPos};
use heapless::String;

pub enum PinPageMsg {
    Confirmed,
    Cancelled,
}

const MAX_LENGTH: usize = 50;

pub struct PinPage {
    pad: Pad,
    prev: Button<&'static str>,
    next: Button<&'static str>,
    accept_pin: Button<&'static str>,
    cancel_pin: Button<&'static str>,
    ok: Button<&'static str>,
    pin_counter: u8,
    pin_buffer: String<MAX_LENGTH>,
}

// TODO: somehow allow for viewing the PIN
// TODO: somehow allow for deleting the digits in PIN

impl PinPage {
    pub fn new() -> Self {
        Self {
            pad: Pad::with_background(theme::BG),
            prev: Button::with_text(ButtonPos::Left, "BACK", theme::button_default()),
            next: Button::with_text(ButtonPos::Right, "NEXT", theme::button_default()),
            accept_pin: Button::with_text(ButtonPos::Left, "ACCEPT", theme::button_default()),
            cancel_pin: Button::with_text(ButtonPos::Right, "CANCEL", theme::button_cancel()),
            ok: Button::with_text(ButtonPos::Middle, "OK", theme::button_default()),
            pin_counter: 0,
            pin_buffer: String::new(),
        }
    }

    fn update_situation(&mut self) {
        // So that only relevant buttons are visible
        self.pad.clear();

        self.show_pin_length();
        self.show_current_digit();
    }

    fn show_pin_length(&mut self) {
        // String::repeat() is not available for heapless::String
        let mut dots: String<50> = String::new();
        for _ in 0..self.pin_buffer.len() {
            dots.push_str("*").unwrap();
        }
        display::text(
            Point::new(0, 20),
            &dots,
            theme::FONT_BOLD,
            theme::FG,
            theme::BG,
        );
    }

    fn show_current_digit(&mut self) {
        let digit: String<1> = String::from(self.pin_counter);
        display::text(
            Point::new(62, 62),
            &digit,
            theme::FONT_BOLD,
            theme::FG,
            theme::BG,
        );
    }

    pub fn pin(&self) -> &str {
        &self.pin_buffer
    }
}

impl Component for PinPage {
    type Msg = PinPageMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let button_height = theme::FONT_BOLD.line_height() + 2;
        let (_content_area, button_area) = bounds.split_bottom(button_height);
        self.pad.place(bounds);
        self.prev.place(button_area);
        self.next.place(button_area);
        self.ok.place(button_area);
        self.accept_pin.place(button_area);
        self.cancel_pin.place(button_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if self.pin_counter > 0 {
            if let Some(ButtonMsg::Clicked) = self.prev.event(ctx, event) {
                // Clicked BACK. Decrease the number.
                self.pin_counter = self.pin_counter - 1;
                self.update_situation();
                return None;
            }
        } else if let Some(ButtonMsg::Clicked) = self.accept_pin.event(ctx, event) {
            // Clicked ACCEPT. Sending the whole PIN string to the client.
            return Some(PinPageMsg::Confirmed);
        }

        if self.pin_counter < 9 {
            if let Some(ButtonMsg::Clicked) = self.next.event(ctx, event) {
                // Clicked NEXT. Increase the number.
                self.pin_counter = self.pin_counter + 1;
                self.update_situation();
                return None;
            }
        } else if let Some(ButtonMsg::Clicked) = self.cancel_pin.event(ctx, event) {
            // Clicked CANCEL. Sending CANCELLED to the client.
            return Some(PinPageMsg::Cancelled);
        }

        if let Some(ButtonMsg::Clicked) = self.ok.event(ctx, event) {
            // Clicked OK. Append current digit to the buffer PIN string.
            let digit_as_str: String<1> = String::from(self.pin_counter);
            self.pin_buffer.push_str(&digit_as_str).unwrap();

            self.update_situation();

            // Changing all other button's visual state to "released" state
            // (one of the buttons has a "pressed" state from
            // the first press of the double-press)
            // NOTE: does not cause any event to the button, it just repaints it
            self.prev.set_released(ctx);
            self.next.set_released(ctx);
            self.accept_pin.set_released(ctx);
            self.cancel_pin.set_released(ctx);
        }

        None
    }

    fn paint(&mut self) {
        self.pad.paint();
        self.update_situation();
        if self.pin_counter > 0 {
            self.prev.paint();
        } else {
            self.accept_pin.paint();
        }
        if self.pin_counter < 9 {
            self.next.paint();
            self.ok.paint();
        } else {
            self.cancel_pin.paint();
            self.ok.paint();
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for PinPage {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("PinPage");
        t.close();
    }
}
