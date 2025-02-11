use crate::ui::{
    component::{Component, Event, EventCtx},
    geometry::{Insets, Offset, Rect},
    layout_eckhart::{
        component::{Button, ButtonContent, ButtonMsg},
        theme,
    },
    shape::{Bar, Renderer},
};

use heapless::Vec;

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
}

pub enum VerticalMenuMsg {
    Selected(usize),
    /// Left header button clicked
    Back,
    /// Right header button clicked
    Close,
}

impl VerticalMenu {
    const SIDE_INSET: i16 = 24;
    const BUTTON_PADDING: i16 = 28;

    fn new(buttons: VerticalMenuButtons) -> Self {
        Self {
            virtual_bounds: Rect::zero(),
            bounds: Rect::zero(),
            buttons,
            separators: false,
            offset_y: 0,
            max_offset: 0,
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
        unwrap!(self.buttons.push(button.styled(theme::menu_item_title())));
        self
    }

    pub fn item_yellow(mut self, button: Button) -> Self {
        unwrap!(self
            .buttons
            .push(button.styled(theme::menu_item_title_yellow())));
        self
    }

    pub fn item_red(mut self, button: Button) -> Self {
        unwrap!(self
            .buttons
            .push(button.styled(theme::menu_item_title_red())));
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
}

impl Component for VerticalMenu {
    type Msg = VerticalMenuMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // Crop the menu area
        self.bounds = bounds.inset(Insets::sides(Self::SIDE_INSET));

        let button_width = self.bounds.width();
        let mut top_left = self.bounds.top_left();

        for button in self.buttons.iter_mut() {
            let button_height = button.content_height() + 2 * Self::BUTTON_PADDING;

            // Calculate button bounds (might overflow the menu bounds)
            let button_bounds =
                Rect::from_top_left_and_size(top_left, Offset::new(button_width, button_height));
            button.place(button_bounds);

            top_left = top_left + Offset::y(button_height);
        }

        // Calculate virtual bounds of all buttons combined
        let height = top_left.y - self.bounds.top_left().y;
        self.virtual_bounds = Rect::from_top_left_and_size(
            self.bounds.top_left(),
            Offset::new(self.bounds.width(), height),
        );

        // Calculate maximum offset for scrolling
        self.max_offset = (self.virtual_bounds.height() - self.bounds.height()).max(0);
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
                // Render menu button
                for button in (&self.buttons).into_iter() {
                    button.render(target);
                }

                // Render separators between buttons
                if self.separators {
                    for i in 1..self.buttons.len() {
                        let button = self.buttons.get(i).unwrap();

                        // Render a line above the button
                        let separator = Rect::from_top_left_and_size(
                            button.area().top_left(),
                            Offset::new(button.area().width(), 1),
                        );
                        Bar::new(separator)
                            .with_fg(theme::GREY_EXTRA_DARK)
                            .render(target);
                    }
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
