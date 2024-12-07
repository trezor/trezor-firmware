use crate::ui::{display::Color, geometry::Rect, shape, shape::Renderer};

pub struct Pad {
    pub area: Rect,
    pub color: Color,
    clear: bool,
}

impl Pad {
    pub fn with_background(color: Color) -> Self {
        Self {
            color,
            area: Rect::zero(),
            clear: false,
        }
    }

    pub fn with_clear(self) -> Self {
        Self {
            clear: true,
            ..self
        }
    }

    pub fn place(&mut self, area: Rect) {
        self.area = area;
    }

    pub fn clear(&mut self) {
        self.clear = true;
    }

    pub fn cancel_clear(&mut self) {
        self.clear = false;
    }

    pub fn will_paint(&self) -> Option<(Rect, Color)> {
        if self.clear {
            Some((self.area, self.color))
        } else {
            None
        }
    }

    pub fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        shape::Bar::new(self.area)
            .with_bg(self.color)
            .render(target);
    }
}
