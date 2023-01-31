#[cfg(feature = "ui_debug")]
use crate::trace::Trace;
use crate::ui::{
    component::{Child, Component, Event, EventCtx, Pad},
    geometry::Rect,
};

use super::super::{theme, ButtonController, ButtonControllerMsg, ButtonLayout, ButtonPos};

pub enum ChoicePageMsg {
    Choice(usize),
    LeftMost,
    RightMost,
}

const DEFAULT_ITEMS_DISTANCE: i16 = 10;
const DEFAULT_Y_BASELINE: i16 = 20;

pub trait Choice {
    fn paint_center(&self, area: Rect, inverse: bool);
    fn width_center(&self) -> i16 {
        0
    }
    fn paint_left(&self, _area: Rect, _show_incomplete: bool) -> Option<i16> {
        None
    }
    fn paint_right(&self, _area: Rect, _show_incomplete: bool) -> Option<i16> {
        None
    }
    fn btn_layout(&self) -> ButtonLayout {
        ButtonLayout::default_three_icons()
    }
}

/// Interface for a specific component efficiently giving
/// `ChoicePage` all the information it needs to render
/// all the choice pages.
///
/// It avoids the need to store the whole sequence of
/// items in `heapless::Vec` (which caused StackOverflow),
/// but offers a "lazy-loading" way of requesting the
/// items only when they are needed, one-by-one.
/// This way, no more than one item is stored in memory at any time.
pub trait ChoiceFactory {
    #[cfg(feature = "ui_debug")]
    type Item: Choice + Trace;
    #[cfg(not(feature = "ui_debug"))]
    type Item: Choice;
    fn count(&self) -> usize;
    fn get(&self, index: usize) -> Self::Item;
}

/// General component displaying a set of items on the screen
/// and allowing the user to select one of them.
///
/// To be used by other more specific components that will
/// supply a set of `Choice`s (through `ChoiceFactory`)
/// and will receive back the index of the selected choice.
///
/// Each `Choice` is responsible for setting the screen -
/// choosing the button text, their duration, text displayed
/// on screen etc.
///
/// `is_carousel` can be used to make the choice page "infinite" -
/// after reaching one end, users will appear at the other end.
pub struct ChoicePage<F>
where
    F: ChoiceFactory,
{
    choices: F,
    pad: Pad,
    buttons: Child<ButtonController>,
    page_counter: usize,
    /// How many pixels from top should we render the items.
    y_baseline: i16,
    /// How many pixels are between the items.
    items_distance: i16,
    /// Whether the choice page is "infinite" (carousel).
    is_carousel: bool,
    /// Whether we should show items on left/right even when they cannot
    /// be painted entirely (they would be cut off).
    show_incomplete: bool,
    /// Whether to show only the currently selected item, nothing left/right.
    show_only_one_item: bool,
    /// Whether the middle selected item should be painted with
    /// inverse colors - black on white.
    inverse_selected_item: bool,
}

impl<F> ChoicePage<F>
where
    F: ChoiceFactory,
{
    pub fn new(choices: F) -> Self {
        let initial_btn_layout = choices.get(0).btn_layout();

        Self {
            choices,
            pad: Pad::with_background(theme::BG),
            buttons: Child::new(ButtonController::new(initial_btn_layout)),
            page_counter: 0,
            y_baseline: DEFAULT_Y_BASELINE,
            items_distance: DEFAULT_ITEMS_DISTANCE,
            is_carousel: false,
            show_incomplete: false,
            show_only_one_item: false,
            inverse_selected_item: false,
        }
    }

    /// Set the page counter at the very beginning.
    /// Need to update the initial button layout.
    pub fn with_initial_page_counter(mut self, page_counter: usize) -> Self {
        self.page_counter = page_counter;
        let initial_btn_layout = self.choices.get(page_counter).btn_layout();
        self.buttons = Child::new(ButtonController::new(initial_btn_layout));
        self
    }

    /// Enabling the carousel mode.
    pub fn with_carousel(mut self, carousel: bool) -> Self {
        self.is_carousel = carousel;
        self
    }

    /// Show incomplete items, even when they cannot render in their entirety.
    pub fn with_incomplete(mut self, show_incomplete: bool) -> Self {
        self.show_incomplete = show_incomplete;
        self
    }

    /// Show only the currently selected item, nothing left/right.
    pub fn with_only_one_item(mut self, only_one_item: bool) -> Self {
        self.show_only_one_item = only_one_item;
        self
    }

    /// Adjust the horizontal baseline from the top of placement.
    pub fn with_y_baseline(mut self, y_baseline: i16) -> Self {
        self.y_baseline = y_baseline;
        self
    }

    /// Adjust the distance between the items.
    pub fn with_items_distance(mut self, items_distance: i16) -> Self {
        self.items_distance = items_distance;
        self
    }

    /// Resetting the component, which enables reusing the same instance
    /// for multiple choice categories.
    ///
    /// Used for example in passphrase, where there are multiple categories of
    /// characters.
    pub fn reset(
        &mut self,
        ctx: &mut EventCtx,
        new_choices: F,
        new_page_counter: Option<usize>,
        is_carousel: bool,
    ) {
        self.choices = new_choices;
        if let Some(new_counter) = new_page_counter {
            self.page_counter = new_counter;
        }
        self.is_carousel = is_carousel;
        self.update(ctx);
    }

    /// Navigating to the chosen page index.
    pub fn set_page_counter(&mut self, ctx: &mut EventCtx, page_counter: usize) {
        self.page_counter = page_counter;
        self.update(ctx);
    }

    /// Display current, previous and next choices according to
    /// the current ChoiceItem.
    fn paint_choices(&mut self) {
        let available_area = self.pad.area.split_top(self.y_baseline).0;

        // Drawing the current item in the middle.
        self.show_current_choice(available_area);

        // Not drawing the rest when not wanted
        if self.show_only_one_item {
            return;
        }

        // Getting the remaining left and right areas.
        let center_width = self.choices.get(self.page_counter).width_center();
        let (left_area, _center_area, right_area) = available_area.split_center(center_width);

        // Possibly drawing on the left side.
        if self.has_previous_choice() || self.is_carousel {
            self.show_left_choices(left_area);
        }

        // Possibly drawing on the right side.
        if self.has_next_choice() || self.is_carousel {
            self.show_right_choices(right_area);
        }
    }

    /// Setting current buttons, and clearing.
    fn update(&mut self, ctx: &mut EventCtx) {
        self.set_buttons(ctx);
        self.clear_and_repaint(ctx);
    }

    /// Clearing the whole area and requesting repaint.
    fn clear_and_repaint(&mut self, ctx: &mut EventCtx) {
        self.pad.clear();
        ctx.request_paint();
    }

    /// Index of the last page.
    fn last_page_index(&self) -> usize {
        self.choices.count() - 1
    }

    /// Whether there is a previous choice (on the left).
    pub fn has_previous_choice(&self) -> bool {
        self.page_counter > 0
    }

    /// Whether there is a next choice (on the right).
    pub fn has_next_choice(&self) -> bool {
        self.page_counter < self.last_page_index()
    }

    /// Display the current choice in the middle.
    fn show_current_choice(&mut self, area: Rect) {
        self.choices
            .get(self.page_counter)
            .paint_center(area, self.inverse_selected_item);

        // Color inversion is just one-time thing.
        if self.inverse_selected_item {
            self.inverse_selected_item = false;
        }
    }

    /// Display all the choices fitting on the left side.
    /// Going as far as possible.
    fn show_left_choices(&self, area: Rect) {
        // page index can get negative here, so having it as i16 instead of usize
        let mut page_index = self.page_counter as i16 - 1;
        let mut x_offset = 0;
        loop {
            // Breaking out of the loop if we exhausted left items
            // and the carousel mode is not enabled.
            if page_index < 0 {
                if self.is_carousel {
                    // Moving to the last page.
                    page_index = self.last_page_index() as i16;
                } else {
                    break;
                }
            }

            let current_area = area.split_right(x_offset + self.items_distance).0;

            if let Some(width) = self
                .choices
                .get(page_index as usize)
                .paint_left(current_area, self.show_incomplete)
            {
                // Updating loop variables.
                x_offset += width + self.items_distance;
                page_index -= 1;
            } else {
                break;
            }
        }
    }

    /// Display all the choices fitting on the right side.
    /// Going as far as possible.
    fn show_right_choices(&self, area: Rect) {
        let mut page_index = self.page_counter + 1;
        let mut x_offset = 3; // starts with a little offset to account for the middle highlight
        loop {
            // Breaking out of the loop if we exhausted right items
            // and the carousel mode is not enabled.
            if page_index > self.last_page_index() {
                if self.is_carousel {
                    // Moving to the first page.
                    page_index = 0;
                } else {
                    break;
                }
            }
            let current_area = area.split_left(x_offset + self.items_distance).1;

            if let Some(width) = self
                .choices
                .get(page_index as usize)
                .paint_right(current_area, self.show_incomplete)
            {
                // Updating loop variables.
                x_offset += width + self.items_distance;
                page_index += 1;
            } else {
                break;
            }
        }
    }

    /// Decrease the page counter to the previous page.
    fn decrease_page_counter(&mut self) {
        self.page_counter -= 1;
    }

    /// Advance page counter to the next page.
    fn increase_page_counter(&mut self) {
        self.page_counter += 1;
    }

    /// Set page to the first one.
    fn page_counter_to_zero(&mut self) {
        self.page_counter = 0;
    }

    /// Set page to the last one.
    fn page_counter_to_max(&mut self) {
        self.page_counter = self.last_page_index();
    }

    /// Get current page counter.
    pub fn page_index(&self) -> usize {
        self.page_counter
    }

    /// Updating the visual state of the buttons after each event.
    /// All three buttons are handled based upon the current choice.
    /// If defined in the current choice, setting their text,
    /// whether they are long-pressed, and painting them.
    fn set_buttons(&mut self, ctx: &mut EventCtx) {
        // TODO: offer the possibility to change the buttons from the client
        // (button details could be changed in the same index)
        // Use-case: BIN button in PIN is deleting last digit if the PIN is not empty,
        // otherwise causing Cancel. Would be nice to allow deleting as a single click
        // and Cancel as HTC. PIN client would check if the PIN is empty/not and
        // adjust the HTC/not.

        let btn_layout = self.choices.get(self.page_counter).btn_layout();
        self.buttons.mutate(ctx, |_ctx, buttons| {
            buttons.set(btn_layout);
        });
    }
}

impl<F> Component for ChoicePage<F>
where
    F: ChoiceFactory,
{
    type Msg = ChoicePageMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (content_area, button_area) = bounds.split_bottom(theme::BUTTON_HEIGHT);
        self.pad.place(content_area);
        self.buttons.place(button_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let button_event = self.buttons.event(ctx, event);

        // Button was "triggered" - released. Doing the appropriate action.
        if let Some(ButtonControllerMsg::Triggered(pos)) = button_event {
            match pos {
                ButtonPos::Left => {
                    if self.has_previous_choice() {
                        // Clicked BACK. Decrease the page counter.
                        self.decrease_page_counter();
                        self.update(ctx);
                    } else if self.is_carousel {
                        // In case of carousel going to the right end.
                        self.page_counter_to_max();
                        self.update(ctx);
                    } else {
                        // Triggered LEFTmost button. Send event
                        self.clear_and_repaint(ctx);
                        return Some(ChoicePageMsg::LeftMost);
                    }
                }
                ButtonPos::Right => {
                    if self.has_next_choice() {
                        // Clicked NEXT. Increase the page counter.
                        self.increase_page_counter();
                        self.update(ctx);
                    } else if self.is_carousel {
                        // In case of carousel going to the left end.
                        self.page_counter_to_zero();
                        self.update(ctx);
                    } else {
                        // Triggered RIGHTmost button. Send event
                        self.clear_and_repaint(ctx);
                        return Some(ChoicePageMsg::RightMost);
                    }
                }
                ButtonPos::Middle => {
                    // Clicked SELECT. Send current choice index
                    self.clear_and_repaint(ctx);
                    return Some(ChoicePageMsg::Choice(self.page_counter));
                }
            }
        };
        // The middle button was "pressed", highlighting the current choice by color
        // inversion.
        if let Some(ButtonControllerMsg::Pressed(ButtonPos::Middle)) = button_event {
            self.inverse_selected_item = true;
            self.clear_and_repaint(ctx);
        };
        None
    }

    fn paint(&mut self) {
        self.pad.paint();
        self.buttons.paint();
        self.paint_choices();
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl<F> crate::trace::Trace for ChoicePage<F>
where
    F: ChoiceFactory,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("ChoicePage");
        t.kw_pair("active_page", &self.page_counter);
        t.kw_pair("page_count", &self.choices.count());
        t.kw_pair("is_carousel", &booltostr!(self.is_carousel));

        if self.has_previous_choice() {
            t.field("prev_choice", &self.choices.get(self.page_counter - 1));
        } else if self.is_carousel {
            // In case of carousel going to the left end.
            t.field("prev_choice", &self.choices.get(self.last_page_index()));
        } else {
            t.string("prev_choice");
            t.symbol("None");
        }
        t.field("current_choice", &self.choices.get(self.page_counter));

        if self.has_next_choice() {
            t.field("next_choice", &self.choices.get(self.page_counter + 1));
        } else if self.is_carousel {
            // In case of carousel going to the very left.
            t.field("next_choice", &self.choices.get(0));
        } else {
            t.string("next_choice");
            t.symbol("None");
        }

        t.field("buttons", &self.buttons);
        t.close();
    }
}
