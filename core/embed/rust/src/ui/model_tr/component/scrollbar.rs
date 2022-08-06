use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    display,
    geometry::{Offset, Point, Rect},
    model_tr::theme,
};

/// In which direction should the scrollbar be positioned
pub enum ScrollbarOrientation {
    Vertical,
    Horizontal,
}

pub struct ScrollBar {
    area: Rect,
    pub page_count: usize,
    pub active_page: usize,
    pub orientation: ScrollbarOrientation,
}

impl ScrollBar {
    pub const WIDTH: i32 = 8;
    pub const DOT_SIZE: Offset = Offset::new(4, 4);
    pub const DOT_INTERVAL: i32 = 6;

    pub fn new(page_count: usize, orientation: ScrollbarOrientation) -> Self {
        Self {
            area: Rect::zero(),
            page_count,
            active_page: 0,
            orientation,
        }
    }

    /// Page count will be given later as it is not available yet.
    pub fn vertical_to_be_filled_later() -> Self {
        Self::vertical(0)
    }

    pub fn vertical(page_count: usize) -> Self {
        Self::new(page_count, ScrollbarOrientation::Vertical)
    }

    pub fn horizontal(page_count: usize) -> Self {
        Self::new(page_count, ScrollbarOrientation::Horizontal)
    }

    pub fn set_page_count(&mut self, page_count: usize) {
        self.page_count = page_count;
    }

    pub fn set_active_page(&mut self, active_page: usize) {
        self.active_page = active_page;
    }

    pub fn has_next_page(&self) -> bool {
        self.active_page < self.page_count - 1
    }

    pub fn has_previous_page(&self) -> bool {
        self.active_page > 0
    }

    pub fn go_to_next_page(&mut self) {
        self.active_page = self.active_page.saturating_add(1).min(self.page_count - 1);
    }

    pub fn go_to_previous_page(&mut self) {
        self.active_page = self.active_page.saturating_sub(1);
    }

    /// Create a (seemingly circular) dot given its top left point.
    /// Make it full when it is active, otherwise paint just the perimeter and leave center empty.
    fn paint_dot(&self, active: bool, top_left: Point) {
        let full_square = Rect::from_top_left_and_size(top_left, ScrollBar::DOT_SIZE);

        // FG - painting the full square
        display::rect_fill(full_square, theme::FG);

        // BG - erase four corners
        for p in full_square.corner_points().iter() {
            display::paint_point(p, theme::BG);
        }

        // BG - erasing the middle when not active
        if !active {
            display::rect_fill(full_square.shrink(1), theme::BG)
        }
    }

    fn paint_vertical(&mut self) {
        let count = self.page_count as i32;
        let interval = {
            let available_space = self.area.height();
            let naive_space = count * Self::DOT_INTERVAL;
            if naive_space > available_space {
                available_space / count
            } else {
                Self::DOT_INTERVAL
            }
        };
        let mut top_left = Point::new(
            self.area.center().x - Self::DOT_SIZE.x / 2,
            self.area.center().y - (count / 2) * interval,
        );
        for i in 0..self.page_count {
            self.paint_dot(i == self.active_page, top_left);
            top_left.y += interval;
        }
    }

    fn paint_horizontal(&mut self) {
        let count = self.page_count as i32;
        let interval = {
            let available_space = self.area.width();
            let naive_space = count * Self::DOT_INTERVAL;
            if naive_space > available_space {
                available_space / count
            } else {
                Self::DOT_INTERVAL
            }
        };
        let mut top_left = Point::new(
            self.area.center().x - (count / 2) * interval,
            self.area.center().y - Self::DOT_SIZE.y / 2,
        );
        for i in 0..self.page_count {
            self.paint_dot(i == self.active_page, top_left);
            top_left.x += interval;
        }
    }
}

impl Component for ScrollBar {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.area
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    /// Displaying one dot for each page.
    fn paint(&mut self) {
        // Not showing the scrollbar dot when there is only one page
        if self.page_count <= 1 {
            return;
        }

        if matches!(self.orientation, ScrollbarOrientation::Vertical) {
            self.paint_vertical()
        } else {
            self.paint_horizontal()
        }
    }
}
