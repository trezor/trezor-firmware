use crate::ui::{
    component::{Component, Event, EventCtx, Pad},
    display,
    geometry::{Point, Rect},
};
use core::ops::Deref;

use super::{theme, BothButtonPressHandler, Button, ButtonMsg, ButtonPos};
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
    ok: Button<&'static str>,
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
            ok: Button::with_text(ButtonPos::Middle, "OK", theme::button_default()),
            page_counter: 0,
        }
    }

    fn render_header(&self) {
        self.display_text(Point::new(0, 10), &self.major_prompt);
        if !self.minor_prompt.is_empty() {
            self.display_text(Point::new(0, 20), &self.minor_prompt);
            display::dotted_line(Point::new(0, 25), 128, theme::FG);
        } else {
            display::dotted_line(Point::new(0, 15), 128, theme::FG);
        }
    }

    fn update_situation(&mut self) {
        // So that only relevant buttons are visible
        self.pad.clear();

        // MIDDLE section above buttons
        if self.page_counter == 0 {
            self.show_current_choice();
            self.show_next_choice();
        } else if self.page_counter < self.last_page_index() {
            self.show_previous_choice();
            self.show_current_choice();
            self.show_next_choice();
        } else if self.page_counter == self.last_page_index() {
            self.show_previous_choice();
            self.show_current_choice();
        }
    }

    fn last_page_index(&self) -> u8 {
        self.choices.len() as u8 - 1
    }

    pub fn get_current_choice(&self) -> &str {
        &self.choices[self.page_counter as usize]
    }

    fn show_current_choice(&self) {
        let current = self.get_current_choice();
        self.display_text(Point::new(62, MIDDLE_ROW), current);
    }

    fn show_previous_choice(&self) {
        let previous = &self.choices[(self.page_counter - 1) as usize];
        self.display_text(Point::new(5, MIDDLE_ROW), previous);
    }

    fn show_next_choice(&self) {
        let next = &self.choices[(self.page_counter + 1) as usize];
        self.display_text(Point::new(115, MIDDLE_ROW), next);
    }

    /// Display bold white text on black background
    fn display_text(&self, baseline: Point, text: &str) {
        display::text(baseline, text, theme::FONT_BOLD, theme::FG, theme::BG);
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
        self.ok.place(button_area);
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
        if self.page_counter > 0 {
            if let Some(ButtonMsg::Clicked) = self.prev.event(ctx, event) {
                // Clicked BACK. Decrease the page counter.
                self.page_counter -= 1;
                self.update_situation();
                return None;
            }
        }

        // RIGHT button clicks
        if self.page_counter < self.last_page_index() {
            if let Some(ButtonMsg::Clicked) = self.next.event(ctx, event) {
                // Clicked NEXT. Increase the page counter.
                self.page_counter += 1;
                self.update_situation();
                return None;
            }
        }

        // MIDDLE button clicks
        if let Some(ButtonMsg::Clicked) = self.ok.event(ctx, event) {
            // Clicked OK. Send current choice to the client.
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
        if self.page_counter > 0 {
            self.prev.paint();
        }

        // BOTTOM RIGHT button
        if self.page_counter < self.last_page_index() {
            self.next.paint();
        }

        // BOTTOM MIDDLE button
        self.ok.paint();
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
