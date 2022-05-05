use crate::{
    time::Duration,
    trezorhal::random,
    ui::{
        component::{Component, Event, EventCtx, Pad},
        display,
        geometry::{Point, Rect},
    },
};
use core::ops::Deref;

use super::{theme, BothButtonPressHandler, Button, ButtonMsg, ButtonPos};
use heapless::String;

pub enum PinPageMsg {
    Confirmed,
    Cancelled,
}

const LEFT_COL: i32 = 5;
const MIDDLE_COL: i32 = 50;
const RIGHT_COL: i32 = 90;

const PIN_ROW: i32 = 40;
const MIDDLE_ROW: i32 = 72;

const MAX_LENGTH: usize = 50;
const MAX_VISIBLE_DOTS: usize = 18;
const MAX_VISIBLE_DIGITS: usize = 18;
const HOLD_DURATION: Duration = Duration::from_secs(2);

const DIGITS: [&str; 10] = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"];

pub struct PinPage<T> {
    major_prompt: T,
    minor_prompt: T,
    allow_cancel: bool,
    digits: [&'static str; 10],
    both_button_press: BothButtonPressHandler,
    pad: Pad,
    prev: Button<&'static str>,
    next: Button<&'static str>,
    accept_pin: Button<&'static str>,
    cancel_pin: Button<&'static str>,
    ok: Button<&'static str>,
    reveal_pin: Button<&'static str>,
    delete_last_digit: Button<&'static str>,
    page_counter: u8,
    show_real_pin: bool,
    pin_buffer: String<MAX_LENGTH>,
}

impl<T> PinPage<T>
where
    T: Deref<Target = str>,
{
    pub fn new(major_prompt: T, minor_prompt: T, allow_cancel: bool, shuffle: bool) -> Self {
        let digits = if shuffle {
            let mut digits = DIGITS;
            random::shuffle(&mut digits);
            digits
        } else {
            DIGITS
        };

        Self {
            major_prompt,
            minor_prompt,
            allow_cancel,
            digits,
            both_button_press: BothButtonPressHandler::new(),
            pad: Pad::with_background(theme::BG),
            prev: Button::with_text(ButtonPos::Left, "<", theme::button_default()),
            next: Button::with_text(ButtonPos::Right, ">", theme::button_default()),
            accept_pin: Button::with_text(ButtonPos::Middle, "CONFIRM", theme::button_default())
                .with_long_press(HOLD_DURATION),
            cancel_pin: Button::with_text(ButtonPos::Left, "BIN", theme::button_cancel())
                .with_long_press(HOLD_DURATION),
            ok: Button::with_text(ButtonPos::Middle, "SELECT", theme::button_default()),
            reveal_pin: Button::with_text(ButtonPos::Middle, "SHOW", theme::button_default()),
            delete_last_digit: Button::with_text(ButtonPos::Middle, "DEL", theme::button_default()),
            page_counter: 0,
            show_real_pin: false,
            pin_buffer: String::new(),
        }
    }

    fn render_header(&self) {
        self.display_text(Point::new(0, 10), &self.major_prompt);
        self.display_text(Point::new(0, 20), &self.minor_prompt);
        display::dotted_line(Point::new(0, 25), 128, theme::FG);
    }

    fn update_situation(&mut self) {
        // So that only relevant buttons are visible
        self.pad.clear();

        // TOP section under header
        self.show_pin_length();

        // MIDDLE section above buttons
        if self.page_counter == 0 {
            self.show_prompt(MIDDLE_COL);
            self.show_next_digit();
        } else if self.page_counter == 1 {
            self.show_prompt(LEFT_COL);
            self.show_current_digit();
            self.show_next_digit();
        } else if self.page_counter < 11 {
            self.show_previous_digit();
            self.show_current_digit();
            self.show_next_digit();
        } else {
            self.show_previous_digit();
            self.show_current_digit();
        }
    }

    fn show_prompt(&self, x: i32) {
        self.display_text(Point::new(x, MIDDLE_ROW), "ENTER");
        self.display_text(Point::new(x, MIDDLE_ROW + 10), "PIN");
    }

    fn show_pin_length(&self) {
        // Only showing the maximum visible length
        let digits = self.pin_buffer.len();
        let dots_visible = digits.min(MAX_VISIBLE_DOTS);

        // String::repeat() is not available for heapless::String
        let mut dots: String<50> = String::new();
        for _ in 0..dots_visible {
            dots.push_str("*").unwrap();
        }

        // Giving some notion of change even for longer-than-visible PINs
        // - slightly shifting the dots to the left and right after each new digit
        if digits > MAX_VISIBLE_DOTS && digits % 2 == 0 {
            self.display_text_center(Point::new(61, PIN_ROW), &dots);
        } else {
            self.display_text_center(Point::new(64, PIN_ROW), &dots);
        }
    }

    fn reveal_current_pin(&self) {
        let digits = self.pin_buffer.len();

        if digits <= MAX_VISIBLE_DOTS {
            self.display_text_center(Point::new(64, PIN_ROW), &self.pin_buffer);
        } else {
            // Show the last part of PIN with preceding ellipsis to show something is hidden
            let ellipsis = "...";
            let offset: usize = digits.saturating_sub(MAX_VISIBLE_DIGITS) + ellipsis.len();
            let mut to_show: String<MAX_VISIBLE_DIGITS> = String::from(ellipsis);
            to_show.push_str(&self.pin_buffer[offset..]).unwrap();
            self.display_text_center(Point::new(32, PIN_ROW), &to_show);
        }
    }

    fn show_reveal_pin_option(&self, x: i32) {
        // self.display_text(Point::new(5, 72), "Reveal current PIN");
        self.display_text(Point::new(x, MIDDLE_ROW), "Show");
        self.display_text(Point::new(x, MIDDLE_ROW + 10), "curr");
        self.display_text(Point::new(x, MIDDLE_ROW + 20), "PIN");
    }

    fn delete_last_digit(&mut self) {
        self.pin_buffer.pop();
    }

    fn show_delete_last_digit_option(&self, x: i32) {
        // self.display_text(Point::new(5, 72), "Delete last digit");
        self.display_text(Point::new(x, MIDDLE_ROW), "Del");
        self.display_text(Point::new(x, MIDDLE_ROW + 10), "last");
        self.display_text(Point::new(x, MIDDLE_ROW + 20), "digit");
    }

    fn get_current_digit(&self) -> &'static str {
        &self.digits[(self.page_counter - 1) as usize]
    }

    fn show_current_digit(&self) {
        let current = self.get_current_digit();
        self.display_text(Point::new(62, MIDDLE_ROW), &current);
    }

    fn show_previous_digit(&self) {
        if self.page_counter > 1 {
            let previous = self.digits[(self.page_counter - 2) as usize];
            self.display_text(Point::new(5, MIDDLE_ROW), &previous);
        }
    }

    fn show_next_digit(&self) {
        if self.page_counter < 10 {
            let next = self.digits[(self.page_counter) as usize];
            self.display_text(Point::new(115, MIDDLE_ROW), &next);
        }
    }

    /// Display bold white text on black background
    fn display_text(&self, baseline: Point, text: &str) {
        display::text(baseline, text, theme::FONT_BOLD, theme::FG, theme::BG);
    }

    /// Display bold white text on black background, centered around a baseline
    /// Point
    fn display_text_center(&self, baseline: Point, text: &str) {
        display::text_center(baseline, text, theme::FONT_BOLD, theme::FG, theme::BG);
    }

    pub fn pin(&self) -> &str {
        &self.pin_buffer
    }

    fn is_full(&self) -> bool {
        self.pin_buffer.len() == self.pin_buffer.capacity()
    }

    fn is_empty(&self) -> bool {
        self.pin_buffer.is_empty()
    }

    /// Changing all non-middle button's visual state to "released" state
    /// (one of the buttons has a "pressed" state from
    /// the first press of the both-button-press)
    /// NOTE: does not cause any event to the button, it just repaints it
    fn set_right_and_left_buttons_as_released(&mut self, ctx: &mut EventCtx) {
        self.prev.set_released(ctx);
        self.next.set_released(ctx);
        self.accept_pin.set_released(ctx);
        self.cancel_pin.set_released(ctx);
    }
}

impl<T> Component for PinPage<T>
where
    T: Deref<Target = str>,
{
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
        // Possibly replacing or skipping an event because of both-button-press
        // aggregation
        let event = self.both_button_press.possibly_replace_event(event)?;

        // In case of both-button-press, changing all other buttons to released
        // state
        if self.both_button_press.are_both_buttons_pressed(event) {
            self.set_right_and_left_buttons_as_released(ctx);
        }

        // Each event should cancel the visible PIN
        self.show_real_pin = false;

        // LEFT button clicks
        if self.page_counter > 0 {
            if let Some(ButtonMsg::Clicked) = self.prev.event(ctx, event) {
                // Clicked BACK. Decrease the page counter.
                self.page_counter = self.page_counter - 1;
                self.update_situation();
                return None;
            }
        } else if let Some(ButtonMsg::Clicked) = self.cancel_pin.event(ctx, event) {
            // Clicked BIN. Deleting the last digit or cancelling the action when empty.
            if !self.is_empty() {
                self.delete_last_digit();
                self.update_situation();
                return None;
            } else {
                return Some(PinPageMsg::Cancelled);
            }
        }

        // RIGHT button clicks
        if self.page_counter < 10 {
            if let Some(ButtonMsg::Clicked) = self.next.event(ctx, event) {
                // Clicked NEXT. Increase the page counter.
                self.page_counter = self.page_counter + 1;
                self.update_situation();
                return None;
            }
        }

        // MIDDLE button clicks
        if self.page_counter == 0 {
            if let Some(ButtonMsg::Clicked) = self.accept_pin.event(ctx, event) {
                // Clicked ACCEPT. Send PIN to the client.
                return Some(PinPageMsg::Confirmed);
            }
        } else if self.page_counter < 11 {
            if let Some(ButtonMsg::Clicked) = self.ok.event(ctx, event) {
                // Clicked CONFIRM. Append current digit to the buffer PIN string.
                if !self.is_full() {
                    self.pin_buffer.push_str(self.get_current_digit()).unwrap();
                    self.page_counter = 0;
                    self.update_situation();
                    return None;
                }
            }
        }

        None
    }

    fn paint(&mut self) {
        self.pad.paint();

        // TOP header
        // self.render_header();

        // MIDDLE panel
        self.update_situation();

        // BOTTOM LEFT button
        if self.page_counter == 0 {
            self.cancel_pin.paint();
        } else {
            self.prev.paint();
        }

        // BOTTOM RIGHT button
        if self.page_counter < 10 {
            self.next.paint();
        }

        // BOTTOM MIDDLE button
        if self.page_counter == 0 {
            self.accept_pin.paint();
        } else {
            self.ok.paint();
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for PinPage<T>
where
    T: Deref<Target = str>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("PinPage");
        t.close();
    }
}
