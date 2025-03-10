use crate::ui::{
    component::{Component, Event, EventCtx},
    geometry::{Offset, Rect},
    layout_eckhart::{component::ButtonMsg, theme},
    shape::{Bar, Renderer},
};

use super::super::{component::Button, theme::GREY_EXTRA_DARK};
use heapless::Vec;

pub const MENU_MAX_ITEMS: usize = 3;

type VerticalMenuButtons = Vec<Button, MENU_MAX_ITEMS>;

pub struct BldMenu {
    bounds: Rect,
    buttons: VerticalMenuButtons,
}
pub enum BldMenuSelectionMsg {
    Selected(usize),
}

impl BldMenu {
    pub fn new(buttons: VerticalMenuButtons) -> Self {
        Self {
            bounds: Rect::zero(),
            buttons,
        }
    }

    pub fn empty() -> Self {
        Self::new(VerticalMenuButtons::new())
    }

    pub fn item(mut self, button: Button) -> Self {
        unwrap!(self.buttons.push(button));
        self
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
                Bar::new(separator).with_fg(GREY_EXTRA_DARK).render(target);
            }
        }
    }
}

impl Component for BldMenu {
    type Msg = BldMenuSelectionMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // Crop the menu area
        self.bounds = bounds.inset(theme::SIDE_INSETS);

        let button_width = self.bounds.width();
        let mut top_left = self.bounds.top_left();
        let padding = 28;

        for button in self.buttons.iter_mut() {
            let button_height = button.content_height() + 2 * padding;
            let button_bounds =
                Rect::from_top_left_and_size(top_left, Offset::new(button_width, button_height));

            button.place(button_bounds);
            top_left = top_left + Offset::y(button_height);
        }
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        for (i, button) in self.buttons.iter_mut().enumerate() {
            if let Some(ButtonMsg::Clicked) = button.event(ctx, event) {
                return Some(Self::Msg::Selected(i));
            }
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.render_buttons(target);
        self.render_separators(target);
    }
}
