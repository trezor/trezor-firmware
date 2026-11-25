use crate::ui::display::Color;
use crate::ui::geometry::Rect;
use crate::ui::shape;
use crate::ui::shape::Renderer;

pub struct Pad {
    pub area: Rect,
    pub color: Color,
}

impl Pad {
    pub fn with_background(color: Color) -> Self {
        Self {
            color,
            area: Rect::zero(),
        }
    }

    pub fn place(&mut self, area: Rect) {
        self.area = area;
    }

    pub fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        shape::Bar::new(self.area)
            .with_bg(self.color)
            .render(target);
    }
}
