use crate::ui::{
    component::{Component, Event, EventCtx},
    geometry::{Insets, Offset, Rect},
    shape::{Bar, Renderer},
};

use heapless::Vec;

use super::super::{
    component::{Button, ButtonMsg},
    theme,
};

/// Number of buttons.
/// Presently, VerticalMenu holds only fixed number of buttons.
pub const MENU_MAX_ITEMS: usize = 5;

type VerticalMenuButtons = Vec<Button, MENU_MAX_ITEMS>;

pub struct VerticalMenu {
    /// Bounds the sliding window of the menu.
    bounds: Rect,
    /// FUll bounds of the menu, including off-screen items.
    virtual_bounds: Rect,
    /// Menu items.
    buttons: VerticalMenuButtons,
    /// Whether to show separators between buttons.
    separators: bool,
    /// Vertical offset of the current view.
    offset_y: i16,
    /// Maximum vertical offset.
    max_offset: i16,
    /// Adapt padding to fit entire area. If the area is too small, the padding
    /// will be reduced to min value.
    fit_area: bool,
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
            virtual_bounds: Rect::zero(),
            bounds: Rect::zero(),
            buttons,
            separators: false,
            offset_y: 0,
            max_offset: 0,
            fit_area: false,
        }
    }

    pub fn empty() -> Self {
        Self::new(VerticalMenuButtons::new())
    }

    pub fn with_separators(mut self) -> Self {
        self.separators = true;
        self
    }

    pub fn with_fit_area(mut self) -> Self {
        self.fit_area = true;
        self
    }

    pub fn item(mut self, button: Button) -> Self {
        unwrap!(self.buttons.push(button));
        self
    }

    pub fn area(&self) -> Rect {
        self.bounds
    }

    /// Scroll the menu to the desired offset.
    pub fn set_offset(&mut self, offset_y: i16) {
        self.offset_y = offset_y.max(0).min(self.max_offset);
    }

    /// Chcek if the menu is on the bottom.
    pub fn is_max_offset(&self) -> bool {
        self.offset_y == self.max_offset
    }

    /// Get the current sliding window offset.
    pub fn get_offset(&self) -> i16 {
        self.offset_y
    }

    /// Update menu buttons based on the current offset.
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
        let menu_overflow = (self.virtual_bounds.height() - self.bounds.height()).max(0);

        // Find the first button from the top that would completely fit in the menu area
        // in the bottom position
        for button in &self.buttons {
            let offset = button.area().top_left().y - self.area().top_left().y;
            if offset > menu_overflow {
                self.max_offset = offset;
                return;
            }
        }

        self.max_offset = menu_overflow;
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
                        .ofs(Offset::x(button.content_offset().x).into()),
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

        // Determine padding dynamically if `fit_area` is enabled
        let padding = if self.fit_area {
            let mut content_height = 0;
            for button in self.buttons.iter_mut() {
                content_height += button.content_height();
            }
            let padding = (self.bounds.height() - content_height) / (self.buttons.len() as i16) / 2;
            padding.max(Self::MIN_PADDING)
        } else {
            Self::DEFAULT_PADDING
        };

        let button_width = self.bounds.width();
        let mut top_left = self.bounds.top_left();

        // Place each button (might overflow the menu bounds)
        for button in self.buttons.iter_mut() {
            let button_height = button.content_height() + 2 * padding;
            let button_bounds =
                Rect::from_top_left_and_size(top_left, Offset::new(button_width, button_height));

            button.place(button_bounds);

            top_left = top_left + Offset::y(button_height);
        }

        // Calculate virtual bounds of all buttons combined
        let total_height = top_left.y - self.bounds.top_left().y;
        self.virtual_bounds = Rect::from_top_left_and_size(
            self.bounds.top_left(),
            Offset::new(self.bounds.width(), total_height),
        );

        // Calculate maximum offset for scrolling
        self.set_max_offset();

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        for (i, button) in self.buttons.iter_mut().enumerate() {
            if let Some(ButtonMsg::Clicked) = button.event(ctx, event) {
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
