use crate::{
    trezorhal::bip39,
    ui::{
        component::{text::common::TextBox, Component, Event, EventCtx, Pad},
        display,
        geometry::{Point, Rect},
    },
    util,
};
use core::ops::Deref;

use super::{common, theme, BothButtonPressHandler, Button, ButtonMsg, ButtonPos};
use heapless::{String, Vec};

pub enum Bip39PageMsg {
    Confirmed,
}

const LETTERS_ROW: i32 = 40;
const MIDDLE_ROW: i32 = 72;

const MAX_LENGTH: usize = 20;

/// Offer words when there will be fewer of them than this
const WORD_THRESHOLD: usize = 10;

pub struct Bip39Page<T> {
    prompt: T,
    letter_choices: Vec<char, 26>,
    both_button_press: BothButtonPressHandler,
    pad: Pad,
    delete: Button<&'static str>,
    prev: Button<&'static str>,
    next: Button<&'static str>,
    select: Button<&'static str>,
    page_counter: u8,
    textbox: TextBox<MAX_LENGTH>,
    offer_words: bool,
    words_list: bip39::Wordlist,
}

impl<T> Bip39Page<T>
where
    T: Deref<Target = str>,
{
    pub fn new(prompt: T) -> Self {
        Self {
            prompt,
            letter_choices: bip39::get_available_letters("").collect(),
            both_button_press: BothButtonPressHandler::new(),
            pad: Pad::with_background(theme::BG),
            delete: Button::with_text(ButtonPos::Left, "BIN", theme::button_default()),
            prev: Button::with_text(ButtonPos::Left, "BACK", theme::button_default()),
            next: Button::with_text(ButtonPos::Right, "NEXT", theme::button_default()),
            select: Button::with_text(ButtonPos::Middle, "SELECT", theme::button_default()),
            page_counter: 0,
            textbox: TextBox::empty(),
            offer_words: false,
            words_list: bip39::Wordlist::all(),
        }
    }

    /// Gets up-to-date choices for letters or words.
    fn reflect_letter_change(&mut self) {
        self.words_list = self.words_list.filter_prefix(self.textbox.content());

        if self.words_list.len() < WORD_THRESHOLD {
            self.offer_words = true;
        } else {
            self.offer_words = false;
            self.letter_choices = bip39::get_available_letters(self.textbox.content()).collect();
        }

        self.page_counter = 0;
    }

    fn render_header(&self) {
        common::display_text(Point::new(0, 10), &self.prompt);
        display::dotted_line(Point::new(0, 15), 128, theme::FG);
    }

    fn update_situation(&mut self) {
        // So that only relevant buttons are visible
        self.pad.clear();

        // TOP section under header
        self.show_current_letters();

        // MIDDLE section above buttons
        if self.page_counter == 0 {
            self.show_current_choice();
            self.show_next_choice();
        } else if self.is_there_next_choice() {
            self.show_previous_choice();
            self.show_current_choice();
            self.show_next_choice();
        } else {
            self.show_previous_choice();
            self.show_current_choice();
        }
    }

    fn show_current_letters(&self) {
        let to_show = build_string!({ MAX_LENGTH + 1 }, self.textbox.content(), "_");
        common::display_text_center(Point::new(61, LETTERS_ROW), &to_show);
    }

    fn last_page_index(&self) -> u8 {
        if self.offer_words {
            self.words_list.len() as u8 - 1
        } else {
            self.letter_choices.len() as u8 - 1
        }
    }

    fn append_current_letter(&mut self, ctx: &mut EventCtx) {
        self.textbox.append(ctx, self.get_current_letter());
    }

    fn delete_last_letter(&mut self, ctx: &mut EventCtx) {
        self.textbox.delete_last(ctx);
    }

    fn reset_wordlist(&mut self) {
        self.words_list = bip39::Wordlist::all();
    }

    fn increase_counter(&mut self) {
        self.page_counter += 1;
    }

    fn decrease_counter(&mut self) {
        self.page_counter -= 1;
    }

    fn is_empty(&self) -> bool {
        self.textbox.is_empty()
    }

    pub fn get_current_choice(&self) -> String<20> {
        self.get_choice(self.page_counter)
    }

    fn get_previous_choice(&self) -> String<20> {
        self.get_choice(self.page_counter - 1)
    }

    fn get_next_choice(&self) -> String<20> {
        self.get_choice(self.page_counter + 1)
    }

    fn get_choice(&self, index: u8) -> String<20> {
        if self.offer_words {
            String::from(self.words_list.get(index as usize).unwrap_or_default())
        } else {
            util::char_to_string(self.letter_choices[index as usize])
        }
    }

    fn get_current_letter(&self) -> char {
        self.letter_choices[self.page_counter as usize]
    }

    fn is_there_next_choice(&self) -> bool {
        self.page_counter < self.last_page_index()
    }

    fn show_current_choice(&self) {
        common::display_text_center(Point::new(64, MIDDLE_ROW + 10), &self.get_current_choice());
    }

    fn show_previous_choice(&self) {
        common::display_text(Point::new(5, MIDDLE_ROW), &self.get_previous_choice());
    }

    fn show_next_choice(&self) {
        common::display_text_right(Point::new(123, MIDDLE_ROW), &self.get_next_choice());
    }

    /// Changing all non-middle button's visual state to "released" state
    /// (one of the buttons has a "pressed" state from
    /// the first press of the both-button-press)
    /// NOTE: does not cause any event to the button, it just repaints it
    fn set_right_and_left_buttons_as_released(&mut self, ctx: &mut EventCtx) {
        self.delete.set_released(ctx);
        self.prev.set_released(ctx);
        self.next.set_released(ctx);
    }
}

impl<T> Component for Bip39Page<T>
where
    T: Deref<Target = str>,
{
    type Msg = Bip39PageMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let button_height = theme::FONT_BOLD.line_height() + 2;
        let (_content_area, button_area) = bounds.split_bottom(button_height);
        self.pad.place(bounds);
        self.delete.place(button_area);
        self.prev.place(button_area);
        self.next.place(button_area);
        self.select.place(button_area);
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

        // LEFT button clicks
        if self.page_counter == 0 {
            if !self.is_empty() {
                if let Some(ButtonMsg::Clicked) = self.prev.event(ctx, event) {
                    // Clicked BIN. Delete last letter.
                    // As deleting a letter is increasing the group of possible words,
                    // we need to reset the wordlist and start filtering it again
                    self.delete_last_letter(ctx);
                    self.reset_wordlist();
                    self.reflect_letter_change();
                    self.update_situation();
                    return None;
                }
            }
        } else if let Some(ButtonMsg::Clicked) = self.prev.event(ctx, event) {
            // Clicked BACK. Decrease the page counter.
            self.decrease_counter();
            self.update_situation();
            return None;
        }

        // RIGHT button clicks
        if self.is_there_next_choice() {
            if let Some(ButtonMsg::Clicked) = self.next.event(ctx, event) {
                // Clicked NEXT. Increase the page counter.
                self.increase_counter();
                self.update_situation();
                return None;
            }
        }

        // MIDDLE button clicks
        if let Some(ButtonMsg::Clicked) = self.select.event(ctx, event) {
            if self.offer_words {
                // Clicked OK when word is there. Send current choice to the client.
                return Some(Bip39PageMsg::Confirmed);
            } else {
                // Clicked OK when letter is there. Reflect the new situation.
                self.append_current_letter(ctx);
                self.reflect_letter_change();
                self.update_situation();
                return None;
            }
        }

        None
    }

    fn paint(&mut self) {
        self.pad.paint();

        // TOP header
        self.render_header();

        // MIDDLE panel
        self.update_situation();

        // BOTTOM LEFT button
        if self.page_counter == 0 {
            if !self.is_empty() {
                self.delete.paint();
            }
        } else {
            self.prev.paint();
        }

        // BOTTOM RIGHT button
        if self.is_there_next_choice() {
            self.next.paint();
        }

        // BOTTOM MIDDLE button
        self.select.paint();
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Bip39Page<T>
where
    T: Deref<Target = str>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Bip39Page");
        t.close();
    }
}
