use crate::ui::{
    component::{Component, Event, EventCtx},
    event::TouchEvent,
    geometry::{Insets, Offset, Rect},
    shape::{Bar, Renderer},
};

use super::{
    super::component::{Button, ButtonMsg},
    theme,
};
use heapless::Vec;

/// Number of buttons.
/// Presently, VerticalMenu holds only fixed number of buttons.
pub const MENU_MAX_ITEMS: usize = 5;

type VerticalMenuButtons = Vec<Button, MENU_MAX_ITEMS>;

pub struct VerticalMenu {
    /// Bounds the sliding window of the menu.
    bounds: Rect,
    /// Menu items.
    buttons: VerticalMenuButtons,
    /// Full height of the menu, including overflowing items.
    total_height: i16,
    /// Vertical offset of the current view.
    offset_y: i16,
    /// Maximum vertical offset.
    offset_y_max: i16,
    /// Whether to show separators between buttons.
    separators: bool,
}

pub enum VerticalMenuMsg {
    Selected(usize),
}

impl VerticalMenu {
    const SIDE_INSETS: Insets = Insets::sides(12);
    const DEFAULT_PADDING: i16 = 28;
    const MIN_PADDING: i16 = 2;

    fn new(buttons: VerticalMenuButtons) -> Self {
        Self {
            bounds: Rect::zero(),
            buttons,
            total_height: 0,
            offset_y: 0,
            offset_y_max: 0,
            separators: false,
        }
    }

    pub fn empty() -> Self {
        Self::new(VerticalMenuButtons::new())
    }

    pub fn with_separators(mut self) -> Self {
        self.separators = true;
        self
    }

    pub fn item(mut self, button: Button) -> Self {
        unwrap!(self.buttons.push(button));
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
    /// Enable only buttons that are fully visible in the menu area.
    /// Meaningful only if the menu is scrollable.
    /// If the menu fits its area, all buttons are enabled.
    pub fn update_menu(&mut self, ctx: &mut EventCtx) {
        for button in self.buttons.iter_mut() {
            let in_bounds = button
                .area()
                .translate(Offset::y(-self.offset_y))
                .union(self.bounds)
                == self.bounds;
            button.enable_if(ctx, in_bounds);
        }
    }

    fn set_max_offset(&mut self) {
        // Calculate the overflow of the menu area
        let menu_overflow = (self.total_height - self.bounds.height()).max(0);

        // Find the first button from the top that would completely fit in the menu area
        // in the bottom position
        for button in &self.buttons {
            let offset = button.area().top_left().y - self.bounds.top_left().y;
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
        for button in &self.buttons {
            button.render(target);
        }
    }

    fn render_separators<'s>(&'s self, target: &mut impl Renderer<'s>) {
        for i in 1..self.buttons.len() {
            let button = &self.buttons[i];
            let button_prev = &self.buttons[i - 1];

            if !button.is_pressed() && !button_prev.is_pressed() {
                let separator = Rect::from_top_left_and_size(
                    button
                        .area()
                        .top_left()
                        .ofs(Offset::x(button.content_offset().x)),
                    Offset::new(button.area().width() - 2 * button.content_offset().x, 1),
                );
                Bar::new(separator)
                    .with_fg(theme::GREY_EXTRA_DARK)
                    .render(target);
            }
        }
    }
}

impl Component for VerticalMenu {
    type Msg = VerticalMenuMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // Crop the menu area
        self.bounds = bounds.inset(Self::SIDE_INSETS);

        let button_width = self.bounds.width();
        let mut top_left = self.bounds.top_left();

        // Place each button (might overflow the menu bounds)
        for button in self.buttons.iter_mut() {
            let button_height = button.content_height() + 2 * Self::DEFAULT_PADDING;
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
                if self.separators {
                    self.render_separators(target);
                }
            });
        });
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for VerticalMenu {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("VerticalMenu");
        t.in_list("buttons", &|button_list| {
            for button in &self.buttons {
                button_list.child(button);
            }
        });
    }
}
