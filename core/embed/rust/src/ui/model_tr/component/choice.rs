use crate::ui::{
    component::{Component, Event, EventCtx, Pad},
    geometry::Rect,
};

use super::{common::ChoiceItem, theme, BothButtonPressHandler, Button, ButtonMsg, ButtonPos};
use heapless::Vec;

pub enum ChoicePageMsg {
    Choice(u8),
    LeftMost,
    RightMost,
}

const MIDDLE_ROW: i32 = 72;

/// General component displaying a set of items on the screen
/// and allowing the user to select one of them.
///
/// To be used by other more specific components that will
/// supply a set of `ChoiceItem`s and will receive back
/// the index of the selected choice.
///
/// Each `ChoiceItem` is responsible for setting the screen -
/// choosing the button text, their duration, text displayed
/// on screen etc.
pub struct ChoicePage<T, const N: usize> {
    choices: Vec<T, N>,
    both_button_press: BothButtonPressHandler,
    pad: Pad,
    prev: Button<&'static str>,
    next: Button<&'static str>,
    select: Button<&'static str>,
    button_area: Rect,
    page_counter: u8,
}

impl<T, const N: usize> ChoicePage<T, N>
where
    T: ChoiceItem,
{
    pub fn new(choices: Vec<T, N>) -> Self {
        Self {
            choices,
            both_button_press: BothButtonPressHandler::new(),
            pad: Pad::with_background(theme::BG),
            // The button texts are just placeholders,
            // each `ChoiceItem` is responsible for setting those.
            prev: Button::with_text(ButtonPos::Left, "BACK", theme::button_default()),
            next: Button::with_text(ButtonPos::Right, "NEXT", theme::button_default()),
            select: Button::with_text(ButtonPos::Middle, "SELECT", theme::button_default()),
            // Button area is needed so the buttons
            // can be "re-placed" after their text is changed
            // Will be set in `place`
            button_area: Rect::zero(),
            page_counter: 0,
        }
    }

    /// Resetting the component, which enables reusing the same instance
    /// for multiple choice categories.
    ///
    /// NOTE: from the client point of view, it would also be an option to
    /// always create a new instance with fresh setup, but I could not manage to
    /// properly clean up the previous instance - it would still be shown on
    /// screen and colliding with the new one.
    pub fn reset(&mut self, new_choices: Vec<T, N>, reset_page_counter: bool) {
        self.choices = new_choices;
        if reset_page_counter {
            self.set_page_counter(0);
        }
    }

    pub fn set_page_counter(&mut self, page_counter: u8) {
        self.page_counter = page_counter;
    }

    fn update_situation(&mut self) {
        // So that only relevant buttons are visible
        self.pad.clear();

        // MIDDLE section above buttons
        // Performing the appropriate `paint_XXX()` for the main choice
        // and two adjacent choices when present
        self.show_current_choice();
        if self.has_previous_choice() {
            self.show_previous_choice();
        }
        if self.has_next_choice() {
            self.show_next_choice();
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

    fn current_choice(&mut self) -> &mut T {
        &mut self.choices[self.page_counter as usize]
    }

    fn show_current_choice(&mut self) {
        self.choices[self.page_counter as usize].paint_center();
    }

    fn show_previous_choice(&mut self) {
        self.choices[(self.page_counter - 1) as usize].paint_left();
    }

    fn show_next_choice(&mut self) {
        self.choices[(self.page_counter + 1) as usize].paint_right();
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
    T: ChoiceItem,
{
    type Msg = ChoicePageMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let button_height = theme::FONT_BOLD.line_height() + 2;
        let (_content_area, button_area) = bounds.split_bottom(button_height);
        self.pad.place(bounds);
        self.prev.place(button_area);
        self.next.place(button_area);
        self.select.place(button_area);
        // Saving button area so that we can re-place the buttons
        // when when they get updated
        self.button_area = button_area;
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
        if self.current_choice().btn_left().is_some() {
            let left_msg = self.prev.event(ctx, event);
            if left_msg == Some(ButtonMsg::LongPressed) && self.prev.is_longpress()
                || left_msg == Some(ButtonMsg::Clicked) && !self.prev.is_longpress()
            {
                if self.has_previous_choice() {
                    // Clicked BACK. Decrease the page counter.
                    self.decrease_page_counter();
                    return None;
                } else {
                    // Triggered LEFTmost button. Send event
                    return Some(ChoicePageMsg::LeftMost);
                }
            }
        }

        // RIGHT button clicks
        if self.current_choice().btn_right().is_some() {
            let right_msg = self.next.event(ctx, event);
            if right_msg == Some(ButtonMsg::LongPressed) && self.next.is_longpress()
                || right_msg == Some(ButtonMsg::Clicked) && !self.next.is_longpress()
            {
                if self.has_next_choice() {
                    // Clicked NEXT. Increase the page counter.
                    self.increase_page_counter();
                    return None;
                } else {
                    // Triggered RIGHTmost button. Send event
                    return Some(ChoicePageMsg::RightMost);
                }
            }
        }

        // MIDDLE button clicks
        if self.current_choice().btn_middle().is_some() {
            if let Some(ButtonMsg::Clicked) = self.select.event(ctx, event) {
                // Clicked SELECT. Send current choice index
                return Some(ChoicePageMsg::Choice(self.page_counter));
            }
        }

        None
    }

    fn paint(&mut self) {
        self.pad.paint();

        // MIDDLE panel
        self.update_situation();

        // All three buttons are handled based upon the current choice.
        // If defined in the current choice, setting their text,
        // whether they are long-pressed, and painting them.

        // BOTTOM LEFT button
        if let Some(left_btn) = self.current_choice().btn_left() {
            self.prev.set_text(left_btn.text, self.button_area);
            self.prev.set_long_press(left_btn.duration);
            self.prev.paint();
        }
        // BOTTOM MIDDLE button
        if let Some(middle_btn) = self.current_choice().btn_middle() {
            self.select.set_text(middle_btn.text, self.button_area);
            self.select.set_long_press(middle_btn.duration);
            self.select.paint();
        }
        // BOTTOM RIGHT button
        if let Some(right_btn) = self.current_choice().btn_right() {
            self.next.set_text(right_btn.text, self.button_area);
            self.next.set_long_press(right_btn.duration);
            self.next.paint();
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<T, const N: usize> crate::trace::Trace for ChoicePage<T, N>
where
    T: ChoiceItem,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("ChoicePage");
        t.close();
    }
}
