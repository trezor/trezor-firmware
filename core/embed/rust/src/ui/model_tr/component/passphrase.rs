use crate::{
    time::Duration,
    ui::{
        component::{Component, Event, EventCtx, Pad},
        display,
        geometry::{Point, Rect},
    },
};
use core::ops::Deref;

use super::{theme, BothButtonPressHandler, Button, ButtonMsg, ButtonPos};
use heapless::String;

pub enum PassphrasePageMsg {
    Confirmed,
    Cancelled,
}

/// Defines the choices currently available on the screen
#[derive(PartialEq)]
enum ChoiceCategory {
    Menu,
    LowercaseLetter,
    UppercaseLetter,
    Digit,
    SpecialSymbol,
}

const LEFT_COL: i32 = 5;
const MIDDLE_COL: i32 = 50;
const RIGHT_COL: i32 = 90;

const PASSPHRASE_ROW: i32 = 40;
const MIDDLE_ROW: i32 = 72;

const MAX_LENGTH: usize = 100; // just for allocation, then handled by `max_len`
const MAX_VISIBLE_CHARS: usize = 18;
const HOLD_DURATION: Duration = Duration::from_secs(1);

// TODO: could be chars, but then converting to slice/String is tricky
const DIGITS: [&str; 10] = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"];
const LOWERCASE_LETTERS: [&str; 26] = [
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s",
    "t", "u", "v", "w", "x", "y", "z",
];
const UPPERCASE_LETTERS: [&str; 26] = [
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S",
    "T", "U", "V", "W", "X", "Y", "Z",
];
const SPECIAL_SYMBOLS: [&str; 30] = [
    "_", "<", ">", ".", ":", "@", "/", "|", "\\", "!", "(", ")", "+", "%", "&", "-", "[", "]", "?",
    "{", "}", ",", "'", "`", ";", "\"", "~", "$", "^", "=",
];
const MENU: [&str; 4] = ["abc", "ABC", "123", "*#_"];

pub struct PassphrasePage<T> {
    prompt: T,
    max_len: u8,
    lowercase_choices: [&'static str; 26],
    uppercase_choices: [&'static str; 26],
    digits_choices: [&'static str; 10],
    special_choices: [&'static str; 30],
    menu_choices: [&'static str; 4],
    both_button_press: BothButtonPressHandler,
    pad: Pad,
    menu_left: Button<&'static str>,
    menu_right: Button<&'static str>,
    prev: Button<&'static str>,
    next: Button<&'static str>,
    accept: Button<&'static str>,
    cancel: Button<&'static str>,
    ok: Button<&'static str>,
    reveal: Button<&'static str>,
    del: Button<&'static str>,
    page_counter: u8,
    show_plain_passphrase: bool,
    passphrase_buffer: String<MAX_LENGTH>,
    current_category: ChoiceCategory,
}

impl<T> PassphrasePage<T>
where
    T: Deref<Target = str>,
{
    pub fn new(prompt: T, max_len: u8) -> Self {
        Self {
            prompt,
            max_len,
            lowercase_choices: LOWERCASE_LETTERS,
            uppercase_choices: UPPERCASE_LETTERS,
            digits_choices: DIGITS,
            special_choices: SPECIAL_SYMBOLS,
            menu_choices: MENU,
            both_button_press: BothButtonPressHandler::new(),
            pad: Pad::with_background(theme::BG),
            menu_left: Button::with_text(ButtonPos::Left, "MENU", theme::button_default()),
            menu_right: Button::with_text(ButtonPos::Right, "MENU", theme::button_default()),
            prev: Button::with_text(ButtonPos::Left, "BACK", theme::button_default()),
            next: Button::with_text(ButtonPos::Right, "NEXT", theme::button_default()),
            accept: Button::with_text(ButtonPos::Left, "ACCEPT", theme::button_default())
                .with_long_press(HOLD_DURATION),
            cancel: Button::with_text(ButtonPos::Right, "CANCEL", theme::button_cancel())
                .with_long_press(HOLD_DURATION),
            ok: Button::with_text(ButtonPos::Middle, "OK", theme::button_default()),
            reveal: Button::with_text(ButtonPos::Middle, "SHOW", theme::button_default()),
            del: Button::with_text(ButtonPos::Middle, "DEL", theme::button_default()),
            page_counter: 0,
            show_plain_passphrase: false,
            passphrase_buffer: String::new(),
            current_category: ChoiceCategory::Menu,
        }
    }

    fn render_header(&self) {
        self.display_text(Point::new(0, 10), &self.prompt);
        display::dotted_line(Point::new(0, 15), 128, theme::FG);
    }

    fn update_middle_panel(&mut self) {
        // So that only relevant buttons are visible
        self.pad.clear();

        // TOP section under header
        if self.show_plain_passphrase {
            self.reveal_current_passphrase();
        } else {
            self.show_passphrase_length();
        }

        // MIDDLE section above buttons
        if self.page_counter == 0 {
            self.show_current();
            self.show_next();
        } else if self.page_counter < self.last_page() {
            self.show_previous();
            self.show_current();
            self.show_next();
        } else if self.page_counter == self.last_page() {
            self.show_previous();
            self.show_current();
        }

        // MENU is special, as it offers two more screens
        if self.current_category == ChoiceCategory::Menu {
            if self.page_counter == self.last_page() {
                self.show_reveal_passphrase_option(RIGHT_COL);
            } else if self.page_counter == self.last_page() + 1 {
                self.show_previous();
                self.show_reveal_passphrase_option(MIDDLE_COL);
                self.show_delete_last_character_option(RIGHT_COL);
            } else if self.page_counter == self.last_page() + 2 {
                self.show_reveal_passphrase_option(LEFT_COL);
                self.show_delete_last_character_option(MIDDLE_COL);
            }
        }
    }

    fn show_passphrase_length(&self) {
        // Only showing the maximum visible length
        let char_amount = self.passphrase_buffer.len();
        let dots_visible = char_amount.min(MAX_VISIBLE_CHARS);

        // String::repeat() is not available for heapless::String
        let mut dots: String<MAX_LENGTH> = String::new();
        for _ in 0..dots_visible {
            dots.push_str("*").unwrap();
        }

        // Giving some notion of change even for longer-than-visible passphrases
        // - slightly shifting the dots to the left and right after each new digit
        if char_amount > MAX_VISIBLE_CHARS && char_amount % 2 == 0 {
            self.display_text_center(Point::new(61, PASSPHRASE_ROW), &dots);
        } else {
            self.display_text_center(Point::new(64, PASSPHRASE_ROW), &dots);
        }
    }

    fn reveal_current_passphrase(&self) {
        let char_amount = self.passphrase_buffer.len();

        if char_amount <= MAX_VISIBLE_CHARS {
            self.display_text_center(Point::new(64, PASSPHRASE_ROW), &self.passphrase_buffer);
        } else {
            // Show the last part with preceding ellipsis to show something is hidden
            let ellipsis = "...";
            let offset: usize = char_amount.saturating_sub(MAX_VISIBLE_CHARS) + ellipsis.len();
            let mut to_show: String<MAX_VISIBLE_CHARS> = String::from(ellipsis);
            to_show.push_str(&self.passphrase_buffer[offset..]).unwrap();
            self.display_text_center(Point::new(64, PASSPHRASE_ROW), &to_show);
        }
    }

    fn show_reveal_passphrase_option(&self, x: i32) {
        self.display_text(Point::new(x, MIDDLE_ROW), "Show");
        self.display_text(Point::new(x, MIDDLE_ROW + 10), "curr");
        self.display_text(Point::new(x, MIDDLE_ROW + 20), "PIN");
    }

    fn delete_last_character(&mut self) {
        self.passphrase_buffer.pop();
    }

    fn show_delete_last_character_option(&self, x: i32) {
        self.display_text(Point::new(x, MIDDLE_ROW), "Del");
        self.display_text(Point::new(x, MIDDLE_ROW + 10), "last");
        self.display_text(Point::new(x, MIDDLE_ROW + 20), "char");
    }

    fn append_current_char(&mut self) {
        self.passphrase_buffer.push_str(self.get_current()).unwrap();
    }

    fn get_current(&self) -> &'static str {
        self.get(self.page_counter)
    }

    fn get_previous(&self) -> &'static str {
        self.get(self.page_counter - 1)
    }

    fn get_next(&self) -> &'static str {
        self.get(self.page_counter + 1)
    }

    fn get(&self, index: u8) -> &'static str {
        let index = index as usize;
        match self.current_category {
            ChoiceCategory::Menu => self.menu_choices[index],
            ChoiceCategory::LowercaseLetter => self.lowercase_choices[index],
            ChoiceCategory::UppercaseLetter => self.uppercase_choices[index],
            ChoiceCategory::Digit => self.digits_choices[index],
            ChoiceCategory::SpecialSymbol => self.special_choices[index],
        }
    }

    fn last_page(&self) -> u8 {
        match self.current_category {
            ChoiceCategory::Menu => self.menu_choices.len() as u8 - 1,
            ChoiceCategory::LowercaseLetter => self.lowercase_choices.len() as u8 - 1,
            ChoiceCategory::UppercaseLetter => self.uppercase_choices.len() as u8 - 1,
            ChoiceCategory::Digit => self.digits_choices.len() as u8 - 1,
            ChoiceCategory::SpecialSymbol => self.special_choices.len() as u8 - 1,
        }
    }

    fn choose_new_character_category(&mut self) {
        self.current_category = match self.page_counter {
            0 => ChoiceCategory::LowercaseLetter,
            1 => ChoiceCategory::UppercaseLetter,
            2 => ChoiceCategory::Digit,
            3 => ChoiceCategory::SpecialSymbol,
            _ => ChoiceCategory::Menu, // should not happen
        };
    }

    fn choose_menu(&mut self) {
        self.current_category = ChoiceCategory::Menu;
    }

    fn show_current(&self) {
        self.display_text(Point::new(62, MIDDLE_ROW), self.get_current());
    }

    fn show_previous(&self) {
        self.display_text(Point::new(5, MIDDLE_ROW), self.get_previous());
    }

    fn show_next(&self) {
        self.display_text(Point::new(115, MIDDLE_ROW), self.get_next());
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

    pub fn passphrase(&self) -> &str {
        &self.passphrase_buffer
    }

    fn is_full(&self) -> bool {
        self.passphrase_buffer.len() == self.max_len as usize
    }

    fn is_empty(&self) -> bool {
        self.passphrase_buffer.is_empty()
    }

    fn decrease_page_counter(&mut self) {
        self.page_counter -= 1;
    }

    fn increase_page_counter(&mut self) {
        self.page_counter += 1;
    }

    fn reset_page_counter(&mut self) {
        self.page_counter = 0;
    }

    /// Changing all non-middle button's visual state to "released" state
    /// (one of the buttons has a "pressed" state from
    /// the first press of the both-button-press)
    /// NOTE: does not cause any event to the button, it just repaints it
    fn set_right_and_left_buttons_as_released(&mut self, ctx: &mut EventCtx) {
        self.menu_left.set_released(ctx);
        self.menu_right.set_released(ctx);
        self.prev.set_released(ctx);
        self.next.set_released(ctx);
        self.accept.set_released(ctx);
        self.cancel.set_released(ctx);
    }

    fn paint_char_buttons(&mut self) {
        // BOTTOM LEFT button
        if self.page_counter == 0 {
            self.menu_left.paint();
        } else {
            self.prev.paint();
        }

        // BOTTOM MIDDLE button
        if !self.is_full() {
            self.ok.paint();
        }

        // BOTTOM RIGHT button
        if self.page_counter < self.last_page() {
            self.next.paint();
        } else {
            self.menu_right.paint();
        }
    }

    fn paint_menu_buttons(&mut self) {
        // BOTTOM LEFT button
        if self.page_counter == 0 {
            self.accept.paint();
        } else {
            self.prev.paint();
        }

        // BOTTOM MIDDLE button
        if self.page_counter <= self.last_page() {
            self.ok.paint();
        } else if self.page_counter == self.last_page() + 1 && !self.is_empty() {
            self.reveal.paint();
        } else if self.page_counter == self.last_page() + 2 && !self.is_empty() {
            self.del.paint();
        }

        // BOTTOM RIGHT button
        if self.page_counter < self.last_page() + 2 {
            self.next.paint();
        } else {
            self.cancel.paint();
        }
    }

    fn handle_char_event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<PassphrasePageMsg> {
        // LEFT button clicks
        if self.page_counter > 0 {
            if let Some(ButtonMsg::Clicked) = self.prev.event(ctx, event) {
                // Clicked BACK. Decrease the page counter.
                self.decrease_page_counter();
                self.update_middle_panel();
                return None;
            }
        } else if let Some(ButtonMsg::Clicked) = self.menu_left.event(ctx, event) {
            // Clicked MENU. Returning to menu.
            self.choose_menu();
            self.reset_page_counter();
            return None;
        }

        // RIGHT button clicks
        if self.page_counter < self.last_page() {
            if let Some(ButtonMsg::Clicked) = self.next.event(ctx, event) {
                // Clicked NEXT. Increase the page counter.
                self.increase_page_counter();
                self.update_middle_panel();
                return None;
            }
        } else if let Some(ButtonMsg::Clicked) = self.menu_right.event(ctx, event) {
            // Clicked MENU. Returning to menu.
            self.choose_menu();
            self.reset_page_counter();
            return None;
        }

        // MIDDLE button clicks
        if self.page_counter <= self.last_page() {
            if let Some(ButtonMsg::Clicked) = self.ok.event(ctx, event) {
                // Clicked OK. Append current char to the buffer string.
                if !self.is_full() {
                    self.append_current_char();
                    self.update_middle_panel();
                    return None;
                }
            }
        }

        None
    }

    fn handle_menu_event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<PassphrasePageMsg> {
        // LEFT button clicks
        if self.page_counter > 0 {
            if let Some(ButtonMsg::Clicked) = self.prev.event(ctx, event) {
                // Clicked BACK. Decrease the page counter.
                self.decrease_page_counter();
                self.update_middle_panel();
                return None;
            }
        } else if let Some(ButtonMsg::LongPressed) = self.accept.event(ctx, event) {
            // Long-pressed ACCEPT. Sending the passphrase to the client.
            return Some(PassphrasePageMsg::Confirmed);
        }

        // RIGHT button clicks
        if self.page_counter < self.last_page() + 2 {
            if let Some(ButtonMsg::Clicked) = self.next.event(ctx, event) {
                // Clicked NEXT. Increase the page counter.
                self.increase_page_counter();
                self.update_middle_panel();
                return None;
            }
        } else if let Some(ButtonMsg::LongPressed) = self.cancel.event(ctx, event) {
            // Long-pressed CANCEL. Sending CANCELLED to the client.
            return Some(PassphrasePageMsg::Cancelled);
        }

        // MIDDLE button clicks
        if self.page_counter <= self.last_page() {
            if let Some(ButtonMsg::Clicked) = self.ok.event(ctx, event) {
                // Clicked OK. Choose the character category.
                self.choose_new_character_category();
                self.reset_page_counter();
                self.update_middle_panel();
                return None;
            }
        } else if self.page_counter == self.last_page() + 1 {
            if let Some(ButtonMsg::Clicked) = self.reveal.event(ctx, event) {
                if !self.is_empty() {
                    // Clicked SHOW. Showing the current passphrase.
                    self.show_plain_passphrase = true;
                    self.update_middle_panel();
                    return None;
                }
            }
        } else if self.page_counter == self.last_page() + 2 {
            if let Some(ButtonMsg::Clicked) = self.del.event(ctx, event) {
                if !self.is_empty() {
                    // Clicked DEL. Deleting the last character.
                    self.delete_last_character();
                    self.update_middle_panel();
                    return None;
                }
            }
        }

        None
    }
}

impl<T> Component for PassphrasePage<T>
where
    T: Deref<Target = str>,
{
    type Msg = PassphrasePageMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let button_height = theme::FONT_BOLD.line_height() + 2;
        let (_content_area, button_area) = bounds.split_bottom(button_height);
        self.pad.place(bounds);
        self.menu_left.place(button_area);
        self.menu_right.place(button_area);
        self.prev.place(button_area);
        self.next.place(button_area);
        self.ok.place(button_area);
        self.reveal.place(button_area);
        self.del.place(button_area);
        self.accept.place(button_area);
        self.cancel.place(button_area);
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
        self.show_plain_passphrase = false;

        // Handling is different for Menu and all others
        if self.current_category == ChoiceCategory::Menu {
            self.handle_menu_event(ctx, event)
        } else {
            self.handle_char_event(ctx, event)
        }
    }

    fn paint(&mut self) {
        self.pad.paint();

        // TOP header
        self.render_header();

        // MIDDLE panel
        self.update_middle_panel();

        // BOTTOM buttons - different for Menu and all others
        if self.current_category == ChoiceCategory::Menu {
            self.paint_menu_buttons();
        } else {
            self.paint_char_buttons();
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for PassphrasePage<T>
where
    T: Deref<Target = str>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("PassphrasePage");
        t.close();
    }
}
