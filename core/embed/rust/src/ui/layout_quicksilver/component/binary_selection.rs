use crate::ui::{
    component::{Component, Event, EventCtx},
    geometry::{Alignment, Alignment2D, Offset, Rect},
    shape::Renderer,
};

use super::{super::cshape, theme, Button, ButtonContent, ButtonMsg, ButtonStyleSheet};

pub enum BinarySelectionMsg {
    Left,
    Right,
}

/// Component presenting a binary choice represented as two buttons, left and
/// right. Both buttons are parameterized with content and style.
pub struct BinarySelection {
    buttons_area: Rect,
    button_left: Button,
    button_right: Button,
}

impl BinarySelection {
    pub fn new(
        left_content: ButtonContent,
        right_content: ButtonContent,
        left_style: ButtonStyleSheet,
        right_style: ButtonStyleSheet,
    ) -> Self {
        Self {
            buttons_area: Rect::zero(),
            button_left: Button::new(left_content)
                .styled(left_style)
                .with_text_align(Alignment::Center),
            button_right: Button::new(right_content)
                .styled(right_style)
                .with_text_align(Alignment::Center),
        }
    }
}

impl Component for BinarySelection {
    type Msg = BinarySelectionMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // Ensure reasonable space. Other than that, this component fits itself into any
        // bounds.
        let bounds_width = bounds.width();
        let bounds_height = bounds.height();
        assert!(bounds_width > 62);
        assert!(bounds_height > 30);

        let buttons_area = Rect::snap(
            bounds.center(),
            Offset::new(bounds_width, theme::BUTTON_HEIGHT.min(bounds_height)),
            Alignment2D::CENTER,
        );
        let (left_area, _, right_area) = buttons_area.split_center(theme::SPACING);
        self.button_left.place(left_area);
        self.button_right.place(right_area);

        self.buttons_area = buttons_area;
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(ButtonMsg::Clicked) = self.button_left.event(ctx, event) {
            return Some(BinarySelectionMsg::Left);
        }
        if let Some(ButtonMsg::Clicked) = self.button_right.event(ctx, event) {
            return Some(BinarySelectionMsg::Right);
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.button_left.render(target);
        self.button_right.render(target);
        cshape::KeyboardOverlay::new(self.buttons_area).render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for BinarySelection {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("BinarySelection");
        t.child("button_left", &self.button_left);
        t.child("button_right", &self.button_right);
    }
}
