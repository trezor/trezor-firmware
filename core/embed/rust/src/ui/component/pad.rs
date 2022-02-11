use crate::ui::{
    display::{self, Color},
    geometry::Rect,
};

pub struct Pad {
    pub area: Rect,
    color: Color,
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

    pub fn place(&mut self, area: Rect) {
        self.area = area;
    }

    pub fn clear(&mut self) {
        self.clear = true;
    }

    pub fn paint(&mut self) {
        if self.clear {
            self.clear = false;

            display::rect_fill(self.area, self.color);
        }
    }
}
