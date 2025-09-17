use core::ops::DerefMut;

use crate::{
    micropython::gc::GcBox,
    ui::{
        component::{Component, Event, EventCtx},
        event::TouchEvent,
        geometry::{Direction, Insets, Offset, Rect},
        shape::{Bar, Renderer},
        util::animation_disabled,
    },
};

use super::{
    super::component::{Button, ButtonMsg},
    theme,
};
use heapless::Vec;

/// Number of buttons.
/// Presently, VerticalMenu holds only fixed number of buttons.
pub const LONG_MENU_ITEMS: usize = 100;
pub const MEDIUM_MENU_ITEMS: usize = 10;
pub const SHORT_MENU_ITEMS: usize = 5;

pub type LongMenuGc = GcBox<Vec<Button, LONG_MENU_ITEMS>>;
pub type ShortMenuVec = Vec<Button, SHORT_MENU_ITEMS>;
pub type MediumMenuVec = Vec<Button, MEDIUM_MENU_ITEMS>;

pub trait MenuItems: Default {
    fn empty() -> Self {
        Self::default()
    }
    fn push(&mut self, button: Button);
    fn iter(&self) -> core::slice::Iter<'_, Button>;
    fn iter_mut(&mut self) -> core::slice::IterMut<'_, Button>;
    fn get_len(&self) -> usize;
    fn get_last(&self) -> Option<&Button>;
}

impl<const N: usize> MenuItems for Vec<Button, N> {
    fn push(&mut self, button: Button) {
        unwrap!(self.push(button));
    }

    fn iter(&self) -> core::slice::Iter<'_, Button> {
        self.as_slice().iter()
    }

    fn iter_mut(&mut self) -> core::slice::IterMut<'_, Button> {
        self.as_mut_slice().iter_mut()
    }

    fn get_len(&self) -> usize {
        self.len()
    }

    fn get_last(&self) -> Option<&Button> {
        self.last()
    }
}

impl Default for LongMenuGc {
    fn default() -> Self {
        unwrap!(GcBox::new(Vec::new()))
    }
}

impl MenuItems for LongMenuGc {
    fn push(&mut self, button: Button) {
        unwrap!(self.deref_mut().push(button));
    }

    fn iter(&self) -> core::slice::Iter<'_, Button> {
        self.as_slice().iter()
    }

    fn iter_mut(&mut self) -> core::slice::IterMut<'_, Button> {
        self.as_mut_slice().iter_mut()
    }

    fn get_len(&self) -> usize {
        self.len()
    }

    fn get_last(&self) -> Option<&Button> {
        self.last()
    }
}

pub struct VerticalMenu<T = ShortMenuVec> {
    /// Bounds the sliding window of the menu.
    bounds: Rect,
    /// Menu items.
    buttons: T,
    /// Full height of the menu, including overflowing items.
    total_height: i16,
    /// Vertical offset of the current view.
    offset_y: i16,
    /// Maximum vertical offset.
    offset_y_max: i16,
    /// Whether the first button touch area should be shrunk.
    /// If true, the first button will overlap the header.
    /// When using subtitle, the overlap should be disabled.
    top_component_overlap: bool,
}

pub enum VerticalMenuMsg {
    Selected(usize),
}

impl<T: MenuItems> VerticalMenu<T> {
    const SIDE_INSETS: Insets = Insets::sides(12);
    const MENU_ITEM_CONTENT_PADDING: i16 = 32;
    #[cfg(test)]
    pub const TEST_MENU_ITEM_CONTENT_PADDING: i16 = Self::MENU_ITEM_CONTENT_PADDING;

    // Overlap with the header. Must be lower than MENU_ITEM_CONTENT_PADDING so the
    // content is not clipped.
    pub const BUTTON_TOP_SHRINK: i16 = 24;

    fn new(buttons: T) -> Self {
        Self {
            bounds: Rect::zero(),
            buttons,
            total_height: 0,
            offset_y: 0,
            offset_y_max: 0,
            top_component_overlap: true,
        }
    }

    pub fn empty() -> Self {
        Self::new(T::default())
    }

    pub fn with_item(mut self, button: Button) -> Self {
        self.buttons.push(button);
        self
    }

    pub fn item(&mut self, button: Button) -> &mut Self {
        self.buttons.push(button);
        self
    }

    pub fn no_top_component_overlap(&mut self) -> &mut Self {
        self.top_component_overlap = false;
        self
    }

    /// Check if the menu fits its area without scrolling.
    pub fn fits_area(&self) -> bool {
        self.total_height <= self.bounds.height()
    }

    /// Scroll the menu to the desired offset.
    pub fn set_offset(&mut self, offset_y: i16) {
        self.offset_y = offset_y.max(0).min(self.offset_y_max);
    }

    /// Chcek if the menu is on the bottom.
    pub fn is_max_offset(&self) -> bool {
        self.offset_y == self.offset_y_max
    }

    /// Get the current sliding window offset.
    pub fn get_offset(&self) -> i16 {
        self.offset_y
    }

    /// Update state of menu buttons based on the current offset.
    /// Disable only buttons that are fully hidden from the menu view.
    /// Shrink the top button's touch area if it overlaps with the header.
    pub fn update_button_states(&mut self, ctx: &mut EventCtx) {
        for button in self.buttons.iter_mut() {
            let button_shifted_area = button.area().translate(Offset::y(-self.offset_y));
            let intersection = button_shifted_area.clamp(self.bounds);
            let intersection_no_overlap =
                button_shifted_area.clamp(self.bounds.inset(Insets::top(Self::BUTTON_TOP_SHRINK)));
            let fully_hidden = intersection.is_empty();
            // overlap is in the top no-touch overlap area
            let only_in_no_touch_area = self.top_component_overlap
                && intersection.height() <= Self::BUTTON_TOP_SHRINK
                && intersection.top_left() == self.bounds.top_left();
            // Disable button if it is fully outside the menu area or only in the no-touch
            // area
            button.enable_if(ctx, !fully_hidden && !only_in_no_touch_area);

            let is_fully_visible_non_overlap =
                !self.top_component_overlap && intersection.eq(&button_shifted_area);
            let is_fully_visible_overlap =
                self.top_component_overlap && intersection.eq(&intersection_no_overlap);
            let is_bottom_edge_item =
                intersection.bottom_left() != button_shifted_area.bottom_left();

            // Start with a normal touch area
            button.set_expanded_touch_area(Insets::zero());

            // Skip the cases where no shrinking is needed
            if fully_hidden
                || is_fully_visible_non_overlap
                || is_fully_visible_overlap
                || is_bottom_edge_item
                || only_in_no_touch_area
            {
                continue;
            }

            let mut top_shrink = button_shifted_area.height() - intersection.height();
            if self.top_component_overlap {
                top_shrink += Self::BUTTON_TOP_SHRINK;
            }

            button.set_expanded_touch_area(Insets::top(-top_shrink));
        }
    }

    /// Scroll the menu by one item in given direction.
    /// Relevant only for testing purposes when the animations are disabled.
    pub fn scroll_item(&mut self, dir: Direction) {
        // Make sure the animations are disabled
        debug_assert!(animation_disabled());
        // Only vertical swipes are allowed
        debug_assert!(dir == Direction::Up || dir == Direction::Down);

        // For single button, the menu is not scrollable
        if self.buttons.get_len() < 2 {
            return;
        }

        // The offset could reach only discrete values of cumsum of button heights
        let current = self.offset_y;
        let mut cumsum = if self.top_component_overlap {
            -Self::BUTTON_TOP_SHRINK
        } else {
            0
        };

        for button in self
            .buttons
            .iter()
            .take(self.buttons.get_len().saturating_sub(1))
        {
            let new_cumsum = cumsum + button.area().height();
            match dir {
                Direction::Up if new_cumsum > current => {
                    self.set_offset(new_cumsum);
                    break;
                }
                Direction::Down if new_cumsum >= current => {
                    self.set_offset(cumsum);
                    break;
                }
                _ => {
                    cumsum = new_cumsum;
                }
            }
        }
    }

    fn set_max_offset(&mut self) {
        // Relevant only for testing when the animations are disabled
        // The menu is scrollable until the last button is visible
        #[cfg(feature = "ui_debug")]
        if animation_disabled() {
            let offset_y_base = self.total_height
                - self
                    .buttons
                    .get_last()
                    .unwrap_or(&Button::empty())
                    .area()
                    .height();
            self.offset_y_max = if self.top_component_overlap {
                offset_y_base - Self::BUTTON_TOP_SHRINK
            } else {
                offset_y_base
            };
            return;
        }

        // Calculate the overflow of the menu area
        let overflow_base = (self.total_height - self.bounds.height()).max(0);
        let menu_overflow = if self.top_component_overlap {
            (overflow_base - Self::BUTTON_TOP_SHRINK).max(0)
        } else {
            overflow_base
        };

        // Find the first button from the top that would completely fit in the menu area
        // in the bottom position
        for button in self.buttons.iter() {
            let offset_base = (button.area().top_left().y - self.bounds.top_left().y).max(0);
            let offset = if self.top_component_overlap {
                (offset_base - Self::BUTTON_TOP_SHRINK).max(0)
            } else {
                offset_base
            };
            if offset > menu_overflow {
                self.offset_y_max = offset;
                return;
            }
        }

        self.offset_y_max = menu_overflow;
    }

    // Shift position of touch events in the menu area by an offset of the current
    // sliding window position
    fn shift_touch_event(&self, event: Event) -> Event {
        match event {
            Event::Touch(t) => {
                let o = Offset::y(self.offset_y);
                Event::Touch(match t {
                    TouchEvent::TouchStart(p) => TouchEvent::TouchStart(p.ofs(o)),
                    TouchEvent::TouchMove(p) => TouchEvent::TouchMove(p.ofs(o)),
                    TouchEvent::TouchEnd(p) => TouchEvent::TouchEnd(p.ofs(o)),
                })
            }
            _ => event,
        }
    }

    fn render_buttons<'s>(&'s self, target: &mut impl Renderer<'s>) {
        for button in self.buttons.iter() {
            button.render(target);
        }
    }

    fn render_separators<'s>(&'s self, target: &mut impl Renderer<'s>) {
        #[inline]
        fn button_separator(button: &Button) -> Rect {
            Rect::from_top_left_and_size(
                button
                    .area()
                    .top_left()
                    .ofs(Offset::x(button.content_offset().x)),
                Offset::new(button.area().width() - 2 * button.content_offset().x, 1),
            )
        }

        if !self.top_component_overlap {
            if let Some(button) = self.buttons.iter().next() {
                if !button.is_pressed() {
                    Bar::new(button_separator(button))
                        .with_fg(theme::GREY_EXTRA_DARK)
                        .render(target);
                }
            }
        }

        for pair in self.buttons.iter().as_slice().windows(2) {
            let [button_prev, button] = pair else {
                continue;
            };

            if !button.is_pressed() && !button_prev.is_pressed() {
                Bar::new(button_separator(button))
                    .with_fg(theme::GREY_EXTRA_DARK)
                    .render(target);
            }
        }
    }
}

impl<T: MenuItems> Component for VerticalMenu<T> {
    type Msg = VerticalMenuMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // Crop the menu area
        self.bounds = bounds.inset(Self::SIDE_INSETS);

        let button_width = self.bounds.width();
        let mut top_left = self.bounds.top_left();

        // Place each button (might overflow the menu bounds)
        for button in self.buttons.iter_mut() {
            let button_height =
                button.content_height(button_width) + 2 * Self::MENU_ITEM_CONTENT_PADDING;
            let button_bounds =
                Rect::from_top_left_and_size(top_left, Offset::new(button_width, button_height));

            button.place(button_bounds);
            top_left = top_left + Offset::y(button_height);
        }

        // Calculate height of all buttons combined
        self.total_height = top_left.y - self.bounds.top_left().y;

        // Calculate maximum offset for scrolling
        self.set_max_offset();

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Shif touch events by the scroll offset
        let event_shifted = self.shift_touch_event(event);
        for (i, button) in self.buttons.iter_mut().enumerate() {
            if let Some(ButtonMsg::Clicked) = button.event(ctx, event_shifted) {
                return Some(VerticalMenuMsg::Selected(i));
            }
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        // Clip and translate the sliding window based on the scroll offset
        target.in_clip(self.bounds, &|target| {
            target.with_origin(Offset::y(-self.offset_y), &|target| {
                self.render_buttons(target);

                // Render separators between buttons
                self.render_separators(target);
            });
        });
    }
}

#[cfg(feature = "ui_debug")]
impl<T: MenuItems> crate::trace::Trace for VerticalMenu<T> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        // Trace the VerticalMenu component
        t.component("VerticalMenu");

        // Trace the buttons as a list
        t.in_list("buttons", &|button_list| {
            for button in self.buttons.iter() {
                button_list.child(button);
            }
        });
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_overlap_limit() {
        // The overlap must be smaller than the padding so that the text is not clipped
        debug_assert!(
            VerticalMenu::<ShortMenuVec>::BUTTON_TOP_SHRINK
                < VerticalMenu::<ShortMenuVec>::TEST_MENU_ITEM_CONTENT_PADDING
        );
    }
}
