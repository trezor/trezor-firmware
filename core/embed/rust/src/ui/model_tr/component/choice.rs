use crate::ui::{
    component::{Component, Event, EventCtx, Pad},
    display,
    geometry::{Point, Rect},
};
use core::ops::Deref;

use super::{common, theme, BothButtonPressHandler, Button, ButtonMsg, ButtonPos};
use heapless::Vec;

pub enum ChoicePageMsg {
    Confirmed,
}

const MIDDLE_ROW: i32 = 72;

pub struct ChoicePage<T, const N: usize> {
    major_prompt: T,
    minor_prompt: T,
    choices: Vec<T, N>,
    both_button_press: BothButtonPressHandler,
    pad: Pad,
    prev: Button<&'static str>,
    next: Button<&'static str>,
    select: Button<&'static str>,
    page_counter: u8,
}

impl<T, const N: usize> ChoicePage<T, N>
where
    T: Deref<Target = str>,
{
    pub fn new(major_prompt: T, minor_prompt: T, choices: Vec<T, N>) -> Self {
        Self {
            major_prompt,
            minor_prompt,
            choices,
            both_button_press: BothButtonPressHandler::new(),
            pad: Pad::with_background(theme::BG),
            prev: Button::with_text(ButtonPos::Left, "BACK", theme::button_default()),
            next: Button::with_text(ButtonPos::Right, "NEXT", theme::button_default()),
            select: Button::with_text(ButtonPos::Middle, "SELECT", theme::button_default()),
            page_counter: 0,
        }
    }

    fn render_header(&self) {
        common::display_text(Point::new(0, 10), &self.major_prompt);
        if !self.minor_prompt.is_empty() {
            common::display_text(Point::new(0, 20), &self.minor_prompt);
            display::dotted_line(Point::new(0, 25), 128, theme::FG);
        } else {
            display::dotted_line(Point::new(0, 15), 128, theme::FG);
        }
    }

    fn update_situation(&mut self) {
        // So that only relevant buttons are visible
        self.pad.clear();

        // MIDDLE section above buttons
        if !self.has_previous_choice() {
            self.show_current_choice();
            self.show_next_choice();
        } else if self.has_next_choice() {
            self.show_previous_choice();
            self.show_current_choice();
            self.show_next_choice();
        } else {
            self.show_previous_choice();
            self.show_current_choice();
        }
    }

    fn last_page_index(&self) -> u8 {
        self.choices.len() as u8 - 1
    }

    fn has_previous_choice(&self) -> bool {
        self.page_counter > 0
    }

    fn has_next_choice(&self) -> bool {
        self.page_counter < self.last_page_index()
    }

    pub fn get_current_choice(&self) -> &str {
        &self.choices[self.page_counter as usize]
    }

    pub fn get_previous_choice(&self) -> &str {
        &self.choices[(self.page_counter - 1) as usize]
    }

    pub fn get_next_choice(&self) -> &str {
        &self.choices[(self.page_counter + 1) as usize]
    }

    fn show_current_choice(&self) {
        common::display_text_center(Point::new(64, MIDDLE_ROW + 10), self.get_current_choice());
    }

    fn show_previous_choice(&self) {
        common::display_text(Point::new(5, MIDDLE_ROW), self.get_previous_choice());
    }

    fn show_next_choice(&self) {
        common::display_text_right(Point::new(123, MIDDLE_ROW), self.get_next_choice());
    }

    fn decrease_page_counter(&mut self) {
        self.page_counter -= 1;
    }

    fn increase_page_counter(&mut self) {
        self.page_counter += 1;
    }

    /// Changing all non-middle button's visual state to "released" state
    /// (one of the buttons has a "pressed" state from
    /// the first press of the both-button-press)
    /// NOTE: does not cause any event to the button, it just repaints it
    fn set_right_and_left_buttons_as_released(&mut self, ctx: &mut EventCtx) {
        self.prev.set_released(ctx);
        self.next.set_released(ctx);
    }
}

impl<T, const N: usize> Component for ChoicePage<T, N>
where
    T: Deref<Target = str>,
{
    type Msg = ChoicePageMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let button_height = theme::FONT_BOLD.line_height() + 2;
        let (_content_area, button_area) = bounds.split_bottom(button_height);
        self.pad.place(bounds);
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
        if self.has_previous_choice() {
            if let Some(ButtonMsg::Clicked) = self.prev.event(ctx, event) {
                // Clicked BACK. Decrease the page counter.
                self.decrease_page_counter();
                self.update_situation();
                return None;
            }
        }

        // RIGHT button clicks
        if self.has_next_choice() {
            if let Some(ButtonMsg::Clicked) = self.next.event(ctx, event) {
                // Clicked NEXT. Increase the page counter.
                self.increase_page_counter();
                self.update_situation();
                return None;
            }
        }

        // MIDDLE button clicks
        if let Some(ButtonMsg::Clicked) = self.select.event(ctx, event) {
            // Clicked SELECT. Send current choice to the client.
            return Some(ChoicePageMsg::Confirmed);
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
        if self.has_previous_choice() {
            self.prev.paint();
        }

        // BOTTOM RIGHT button
        if self.has_next_choice() {
            self.next.paint();
        }

        // BOTTOM MIDDLE button
        self.select.paint();
    }
}

#[cfg(feature = "ui_debug")]
impl<T, const N: usize> crate::trace::Trace for ChoicePage<T, N>
where
    T: Deref<Target = str>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("ChoicePage");
        t.close();
    }
}
