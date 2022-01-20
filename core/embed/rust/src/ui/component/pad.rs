use crate::ui::{
    display::{self, Color},
    geometry::Rect,
};

pub struct Pad {
    area: Rect,
    color: Color,
    clear: bool,
}

impl Pad {
    pub fn with_background(area: Rect, color: Color) -> Self {
        Self {
            area,
            color,
            clear: false,
        }
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
