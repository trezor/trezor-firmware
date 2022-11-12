use crate::ui::{
    component::{Component, Event, EventCtx, Never, Pad},
    display,
    geometry::{Offset, Point, Rect},
    model_tr::theme,
};

/// Scrollbar to be painted horizontally at the top right of the screen.
pub struct ScrollBar {
    area: Rect,
    pad: Pad,
    pub page_count: usize,
    pub active_page: usize,
}

impl ScrollBar {
    /// How many dots at most will there be
    pub const MAX_DOTS: i16 = 5;
    /// Maximum size (width/height) of a dot
    pub const MAX_DOT_SIZE: i16 = 5;
    /// Distance between two dots
    pub const DOTS_DISTANCE: i16 = 2;
    pub const DOTS_INTERVAL: i16 = Self::MAX_DOT_SIZE + Self::DOTS_DISTANCE;
    pub const MAX_WIDTH: i16 = Self::DOTS_INTERVAL * Self::MAX_DOTS - Self::DOTS_DISTANCE;

    pub fn new(page_count: usize) -> Self {
        Self {
            area: Rect::zero(),
            pad: Pad::with_background(theme::BG),
            page_count,
            active_page: 0,
        }
    }

    /// Page count will be given later as it is not available yet.
    pub fn to_be_filled_later() -> Self {
        Self::new(0)
    }

    pub fn overall_width(&self) -> i16 {
        Self::DOTS_INTERVAL * self.page_count as i16 - Self::DOTS_DISTANCE
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
    /// Make it full when it is active, otherwise paint just the perimeter and
    /// leave center empty.
    fn paint_dot(&self, active: bool, top_right: Point) {
        let full_square =
            Rect::from_top_right_and_size(top_right, Offset::uniform(Self::MAX_DOT_SIZE));

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

    /// Drawing the dots horizontally and aligning to the right
    fn paint_horizontal(&mut self) {
        let mut top_right = self.area.top_right();
        // TODO: implement smaller dots - two more sizes
        // TODO: implement showing at most MAX_DIGITS
        for i in (0..self.page_count).rev() {
            self.paint_dot(i == self.active_page, top_right);
            top_right.x -= Self::DOTS_INTERVAL;
            top_right.print();
        }
    }
}

impl Component for ScrollBar {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.pad.place(bounds);
        bounds
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

        self.pad.clear();
        self.pad.paint();
        self.paint_horizontal();
    }
}
