use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    display,
    geometry::{Insets, Offset, Point, Rect},
    model_tr::theme,
};

pub struct ScrollBar {
    area: Rect,
    pub page_count: usize,
    pub active_page: usize,
}

impl ScrollBar {
    pub const WIDTH: i32 = 8;
    pub const DOT_SIZE: Offset = Offset::new(4, 4);
    pub const DOT_INTERVAL: i32 = 6;

    pub fn vertical() -> Self {
        Self {
            area: Rect::zero(),
            page_count: 0,
            active_page: 0,
        }
    }

    pub fn set_count_and_active_page(&mut self, page_count: usize, active_page: usize) {
        self.page_count = page_count;
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

    fn paint_dot(&self, active: bool, top_left: Point) {
        let sides = [
            Rect::from_top_left_and_size(top_left + Offset::x(1), Offset::new(2, 1)),
            Rect::from_top_left_and_size(top_left + Offset::y(1), Offset::new(1, 2)),
            Rect::from_top_left_and_size(
                top_left + Offset::new(1, Self::DOT_SIZE.y - 1),
                Offset::new(2, 1),
            ),
            Rect::from_top_left_and_size(
                top_left + Offset::new(Self::DOT_SIZE.x - 1, 1),
                Offset::new(1, 2),
            ),
        ];
        for side in sides {
            display::rect_fill(side, theme::FG)
        }
        if active {
            display::rect_fill(
                Rect::from_top_left_and_size(top_left, Self::DOT_SIZE).inset(Insets::uniform(1)),
                theme::FG,
            )
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

    /// Displaying vertical dots on the right side - one for each page.
    fn paint(&mut self) {
        // Not showing the scrollbar dot when there is only one page
        if self.page_count <= 1 {
            return;
        }

        let count = self.page_count as i32;
        let interval = {
            let available_height = self.area.height();
            let naive_height = count * Self::DOT_INTERVAL;
            if naive_height > available_height {
                available_height / count
            } else {
                Self::DOT_INTERVAL
            }
        };
        let mut dot = Point::new(
            self.area.center().x - Self::DOT_SIZE.x / 2,
            self.area.center().y - (count / 2) * interval,
        );
        for i in 0..self.page_count {
            self.paint_dot(i == self.active_page, dot);
            dot.y += interval
        }
    }
}
