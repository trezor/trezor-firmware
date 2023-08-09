use crate::{
    strutil::StringType,
    ui::{
        component::{Child, Component, Event, EventCtx, Pad},
        geometry::{Insets, Offset, Rect},
    },
};

use super::super::{theme, ButtonController, ButtonControllerMsg, ButtonLayout, ButtonPos};

const DEFAULT_ITEMS_DISTANCE: i16 = 10;

pub trait Choice<T: StringType> {
    // Only `paint_center` is required, the rest is optional
    // and therefore has a default implementation.
    fn paint_center(&self, area: Rect, inverse: bool);
    fn width_center(&self) -> i16 {
        0
    }

    fn paint_side(&self, _area: Rect) {}
    fn width_side(&self) -> i16 {
        0
    }

    fn btn_layout(&self) -> ButtonLayout<T> {
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
pub trait ChoiceFactory<T: StringType> {
    type Action;
    type Item: Choice<T>;

    fn count(&self) -> usize;
    fn get(&self, index: usize) -> (Self::Item, Self::Action);
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
pub struct ChoicePage<F, T, A>
where
    F: ChoiceFactory<T, Action = A>,
    T: StringType,
{
    choices: F,
    pad: Pad,
    buttons: Child<ButtonController<T>>,
    page_counter: usize,
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

impl<F, T, A> ChoicePage<F, T, A>
where
    F: ChoiceFactory<T, Action = A>,
    T: StringType + Clone,
{
    pub fn new(choices: F) -> Self {
        let initial_btn_layout = choices.get(0).0.btn_layout();

        Self {
            choices,
            pad: Pad::with_background(theme::BG),
            buttons: Child::new(ButtonController::new(initial_btn_layout)),
            page_counter: 0,
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
        let initial_btn_layout = self.get_current_choice().0.btn_layout();
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
        // Getting the row area for the choices - so that displaying
        // items in the used font will show them in the middle vertically.
        let area_height_half = self.pad.area.height() / 2;
        let font_size_half = theme::FONT_CHOICE_ITEMS.text_height() / 2;
        let center_row_area = self
            .pad
            .area
            .split_top(area_height_half)
            .0
            .outset(Insets::bottom(font_size_half));

        // Drawing the current item in the middle.
        self.show_current_choice(center_row_area);

        // Not drawing the rest when not wanted
        if self.show_only_one_item {
            return;
        }

        // Getting the remaining left and right areas.
        let center_width = self.get_current_choice().0.width_center();
        let (left_area, _center_area, right_area) = center_row_area.split_center(center_width);

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

    /// Getting the choice on the current index
    pub fn get_current_choice(&self) -> (<F as ChoiceFactory<T>>::Item, A) {
        self.choices.get(self.page_counter)
    }

    /// Display the current choice in the middle.
    fn show_current_choice(&mut self, area: Rect) {
        self.get_current_choice()
            .0
            .paint_center(area, self.inverse_selected_item);

        // Color inversion is just one-time thing.
        if self.inverse_selected_item {
            self.inverse_selected_item = false;
        }
    }

    /// Display all the choices fitting on the left side.
    /// Going as far as possible.
    fn show_left_choices(&self, area: Rect) {
        // NOTE: page index can get negative here, so having it as i16 instead of usize
        let mut page_index = self.page_counter as i16 - 1;
        let mut current_area = area.split_right(self.items_distance).0;
        while current_area.width() > 0 {
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

            let (choice, _) = self.choices.get(page_index as usize);
            let choice_width = choice.width_side();

            if current_area.width() <= choice_width && !self.show_incomplete {
                // early break for an item that will not fit the remaining space
                break;
            }

            // We need to calculate the area explicitly because we want to allow it
            // to exceed the bounds of the original area.
            let choice_area = Rect::from_top_right_and_size(
                current_area.top_right(),
                Offset::new(choice_width, current_area.height()),
            );
            choice.paint_side(choice_area);

            // Updating loop variables.
            current_area = current_area
                .split_right(choice_width + self.items_distance)
                .0;
            page_index -= 1;
        }
    }

    /// Display all the choices fitting on the right side.
    /// Going as far as possible.
    fn show_right_choices(&self, area: Rect) {
        let mut page_index = self.page_counter + 1;
        let mut current_area = area.split_left(self.items_distance).1;
        while current_area.width() > 0 {
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

            let (choice, _) = self.choices.get(page_index);
            let choice_width = choice.width_side();

            if current_area.width() <= choice_width && !self.show_incomplete {
                // early break for an item that will not fit the remaining space
                break;
            }

            // We need to calculate the area explicitly because we want to allow it
            // to exceed the bounds of the original area.
            let choice_area = Rect::from_top_left_and_size(
                current_area.top_left(),
                Offset::new(choice_width, current_area.height()),
            );
            choice.paint_side(choice_area);

            // Updating loop variables.
            current_area = current_area
                .split_left(choice_width + self.items_distance)
                .1;
            page_index += 1;
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
        let btn_layout = self.get_current_choice().0.btn_layout();
        self.buttons.mutate(ctx, |_ctx, buttons| {
            buttons.set(btn_layout);
        });
    }

    pub fn choice_factory(&self) -> &F {
        &self.choices
    }
}

impl<F, T, A> Component for ChoicePage<F, T, A>
where
    F: ChoiceFactory<T, Action = A>,
    T: StringType + Clone,
{
    type Msg = A;

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
                    }
                }
                ButtonPos::Middle => {
                    // Clicked SELECT. Send current choice index
                    self.clear_and_repaint(ctx);
                    return Some(self.get_current_choice().1);
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
impl<F, T, A> crate::trace::Trace for ChoicePage<F, T, A>
where
    F: ChoiceFactory<T, Action = A>,
    T: StringType + Clone,
    <F as ChoiceFactory<T>>::Item: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ChoicePage");
        t.int("active_page", self.page_counter as i64);
        t.int("page_count", self.choices.count() as i64);
        t.bool("is_carousel", self.is_carousel);

        if self.has_previous_choice() {
            t.child("prev_choice", &self.choices.get(self.page_counter - 1).0);
        } else if self.is_carousel {
            // In case of carousel going to the left end.
            t.child("prev_choice", &self.choices.get(self.last_page_index()).0);
        }

        t.child("current_choice", &self.choices.get(self.page_counter).0);

        if self.has_next_choice() {
            t.child("next_choice", &self.choices.get(self.page_counter + 1).0);
        } else if self.is_carousel {
            // In case of carousel going to the very left.
            t.child("next_choice", &self.choices.get(0).0);
        }

        t.child("buttons", &self.buttons);
    }
}
