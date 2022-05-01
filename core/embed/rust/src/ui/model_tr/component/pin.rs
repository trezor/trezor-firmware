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
    reveal_pin: Button<&'static str>,
    delete_last_digit: Button<&'static str>,
    pin_counter: u8,
    show_real_pin: bool,
    pin_buffer: String<MAX_LENGTH>,
}

impl PinPage {
    pub fn new() -> Self {
        Self {
            pad: Pad::with_background(theme::BG),
            prev: Button::with_text(ButtonPos::Left, "BACK", theme::button_default()),
            next: Button::with_text(ButtonPos::Right, "NEXT", theme::button_default()),
            accept_pin: Button::with_text(ButtonPos::Left, "ACCEPT", theme::button_default()),
            cancel_pin: Button::with_text(ButtonPos::Right, "CANCEL", theme::button_cancel()),
            ok: Button::with_text(ButtonPos::Middle, "OK", theme::button_default()),
            reveal_pin: Button::with_text(ButtonPos::Middle, "SHOW", theme::button_default()),
            delete_last_digit: Button::with_text(ButtonPos::Middle, "DEL", theme::button_default()),
            pin_counter: 0,
            show_real_pin: false,
            pin_buffer: String::new(),
        }
    }

    fn update_situation(&mut self) {
        // So that only relevant buttons are visible
        self.pad.clear();

        // TODO: find out why it does not work with a boolean
        // input argument into this function
        // (maybe some async?)
        if self.show_real_pin {
            self.reveal_current_pin();
        } else {
            self.show_pin_length();
        }

        if self.pin_counter < 10 {
            self.show_current_digit();
        } else if self.pin_counter == 10 {
            self.show_reveal_pin_option();
        } else if self.pin_counter == 11 {
            self.show_delete_last_digit_option();
        }
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

    fn reveal_current_pin(&mut self) {
        display::text(
            Point::new(0, 20),
            &self.pin_buffer,
            theme::FONT_BOLD,
            theme::FG,
            theme::BG,
        );
    }

    fn show_reveal_pin_option(&mut self) {
        display::text(
            Point::new(5, 62),
            "Reveal current PIN",
            theme::FONT_BOLD,
            theme::FG,
            theme::BG,
        );
    }

    fn delete_last_digit(&mut self) {
        self.pin_buffer.pop();
    }

    fn show_delete_last_digit_option(&mut self) {
        display::text(
            Point::new(5, 62),
            "Delete last digit",
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

    /// Changing all other button's visual state to "released" state
    /// (one of the buttons has a "pressed" state from
    /// the first press of the double-press)
    /// NOTE: does not cause any event to the button, it just repaints it
    fn set_buttons_as_released(&mut self, ctx: &mut EventCtx) {
        self.prev.set_released(ctx);
        self.next.set_released(ctx);
        self.accept_pin.set_released(ctx);
        self.cancel_pin.set_released(ctx);
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
        self.reveal_pin.place(button_area);
        self.delete_last_digit.place(button_area);
        self.accept_pin.place(button_area);
        self.cancel_pin.place(button_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Each event should cancel the visible PIN
        self.show_real_pin = false;

        // LEFT button clicks
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

        // RIGHT button clicks
        if self.pin_counter < 11 {
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

        // MIDDLE button clicks
        if self.pin_counter < 10 {
            if let Some(ButtonMsg::Clicked) = self.ok.event(ctx, event) {
                // Clicked OK. Append current digit to the buffer PIN string.
                let digit_as_str: String<1> = String::from(self.pin_counter);
                self.pin_buffer.push_str(&digit_as_str).unwrap();
                self.update_situation();
                self.set_buttons_as_released(ctx);
                return None;
            }
        } else if self.pin_counter == 10 {
            if let Some(ButtonMsg::Clicked) = self.reveal_pin.event(ctx, event) {
                // Clicked SHOW. Showing the current PIN.
                self.show_real_pin = true;
                self.update_situation();
                self.set_buttons_as_released(ctx);
                return None;
            }
        } else if self.pin_counter == 11 {
            if let Some(ButtonMsg::Clicked) = self.delete_last_digit.event(ctx, event) {
                // Clicked DEL. Deleting the last digit.
                self.delete_last_digit();
                self.update_situation();
                self.set_buttons_as_released(ctx);
                return None;
            }
        }

        None
    }

    fn paint(&mut self) {
        self.pad.paint();
        self.update_situation();

        // LEFT side
        if self.pin_counter > 0 {
            self.prev.paint();
        } else {
            self.accept_pin.paint();
        }

        // RIGHT side
        if self.pin_counter < 11 {
            self.next.paint();
        } else {
            self.cancel_pin.paint();
        }

        // MIDDLE
        if self.pin_counter < 10 {
            self.ok.paint();
        } else if self.pin_counter == 10 {
            self.reveal_pin.paint();
        } else if self.pin_counter == 11 {
            self.delete_last_digit.paint();
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
