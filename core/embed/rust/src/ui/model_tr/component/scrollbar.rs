use crate::ui::{
    component::{Component, Event, EventCtx, Never, Pad},
    display,
    geometry::{Offset, Point, Rect},
    model_tr::theme,
};

use heapless::Vec;

/// Scrollbar to be painted horizontally at the top right of the screen.
pub struct ScrollBar {
    area: Rect,
    pad: Pad,
    pub page_count: usize,
    pub active_page: usize,
}

/// Carrying the appearance of the scrollbar dot.
#[derive(Debug)]
enum DotType {
    BigFull,
    Big,
    Middle,
    Small,
}

/// How many dots at most will there be
const MAX_DOTS: usize = 5;

impl ScrollBar {
    /// Maximum size (width/height) of a dot
    pub const MAX_DOT_SIZE: i16 = 5;
    /// Distance between two dots
    pub const DOTS_DISTANCE: i16 = 2;
    pub const DOTS_INTERVAL: i16 = Self::MAX_DOT_SIZE + Self::DOTS_DISTANCE;
    pub const MAX_WIDTH: i16 = Self::DOTS_INTERVAL * MAX_DOTS as i16 - Self::DOTS_DISTANCE;

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

    /// The width the scrollbar will really occupy.
    pub fn overall_width(&self) -> i16 {
        if self.page_count <= MAX_DOTS {
            Self::DOTS_INTERVAL * self.page_count as i16 - Self::DOTS_DISTANCE
        } else {
            Self::MAX_WIDTH
        }
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
    fn paint_dot(&self, dot_type: &DotType, top_right: Point) {
        let full_square =
            Rect::from_top_right_and_size(top_right, Offset::uniform(Self::MAX_DOT_SIZE));

        match dot_type {
            DotType::BigFull | DotType::Big => {
                // FG - painting the full square
                display::rect_fill(full_square, theme::FG);

                // BG - erase four corners
                for p in full_square.corner_points().iter() {
                    display::paint_point(p, theme::BG);
                }

                // BG - erasing the middle when not full
                if matches!(dot_type, DotType::Big) {
                    display::rect_fill(full_square.shrink(1), theme::BG)
                }
            }
            DotType::Middle => {
                let middle_square = full_square.shrink(1);

                // FG - painting the middle square
                display::rect_fill(middle_square, theme::FG);

                // BG - erase four corners
                for p in middle_square.corner_points().iter() {
                    display::paint_point(p, theme::BG);
                }

                // BG - erasing the middle
                display::rect_fill(middle_square.shrink(1), theme::BG)
            }
            DotType::Small => {
                // FG - painting the small square
                display::rect_fill(full_square.shrink(2), theme::FG)
            }
        }
    }

    /// Get a sequence of dots to be drawn, with specifying their appearance.
    /// Painting only big dots in case of 2 and 3 pages,
    /// three big and 1 middle in case of 4 pages,
    /// and three big, one middle and one small in case of 5 and more pages.
    fn get_drawable_dots(&self) -> Vec<DotType, MAX_DOTS> {
        let mut dots = Vec::new();

        match self.page_count {
            small_num if small_num < 4 => {
                for i in 0..self.page_count {
                    if i == self.active_page {
                        unwrap!(dots.push(DotType::BigFull));
                    } else {
                        unwrap!(dots.push(DotType::Big));
                    }
                }
            }
            4 => {
                match self.active_page {
                    0 => unwrap!(dots.push(DotType::BigFull)),
                    1 => unwrap!(dots.push(DotType::Big)),
                    _ => unwrap!(dots.push(DotType::Middle)),
                };
                match self.active_page {
                    1 => unwrap!(dots.push(DotType::BigFull)),
                    _ => unwrap!(dots.push(DotType::Big)),
                };
                match self.active_page {
                    2 => unwrap!(dots.push(DotType::BigFull)),
                    _ => unwrap!(dots.push(DotType::Big)),
                };
                match self.active_page {
                    3 => unwrap!(dots.push(DotType::BigFull)),
                    2 => unwrap!(dots.push(DotType::Big)),
                    _ => unwrap!(dots.push(DotType::Middle)),
                };
            }
            _ => {
                let full_dot_index = match self.active_page {
                    0 => 0,
                    1 => 1,
                    last if last == self.page_count - 1 => 4,
                    last_but_one if last_but_one == self.page_count - 2 => 3,
                    _ => 2,
                };
                match full_dot_index {
                    0 => unwrap!(dots.push(DotType::BigFull)),
                    1 => unwrap!(dots.push(DotType::Big)),
                    2 => unwrap!(dots.push(DotType::Middle)),
                    _ => unwrap!(dots.push(DotType::Small)),
                };
                match full_dot_index {
                    0 => unwrap!(dots.push(DotType::Big)),
                    1 => unwrap!(dots.push(DotType::BigFull)),
                    2 => unwrap!(dots.push(DotType::Big)),
                    _ => unwrap!(dots.push(DotType::Middle)),
                };
                match full_dot_index {
                    2 => unwrap!(dots.push(DotType::BigFull)),
                    _ => unwrap!(dots.push(DotType::Big)),
                };
                match full_dot_index {
                    0 | 1 => unwrap!(dots.push(DotType::Middle)),
                    3 => unwrap!(dots.push(DotType::BigFull)),
                    _ => unwrap!(dots.push(DotType::Big)),
                };
                match full_dot_index {
                    0 | 1 => unwrap!(dots.push(DotType::Small)),
                    2 => unwrap!(dots.push(DotType::Middle)),
                    3 => unwrap!(dots.push(DotType::Big)),
                    _ => unwrap!(dots.push(DotType::BigFull)),
                };
            }
        }
        dots
    }

    /// Drawing the dots horizontally and aligning to the right.
    fn paint_horizontal(&mut self) {
        let mut top_right = self.area.top_right();
        for dot in self.get_drawable_dots().iter().rev() {
            self.paint_dot(dot, top_right);
            top_right.x -= Self::DOTS_INTERVAL;
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
