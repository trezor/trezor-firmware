use crate::ui::{
    component::{Component, Event, EventCtx, Never, Pad, Paginate},
    geometry::{Offset, Point, Rect},
    shape,
    shape::Renderer,
};

use super::super::theme;

use heapless::Vec;

/// Scrollbar to be painted horizontally at the top right of the screen.
pub struct ScrollBar {
    pad: Pad,
    page_count: usize,
    pub active_page: usize,
}

/// Carrying the appearance of the scrollbar dot.
#[derive(Debug)]
enum DotType {
    BigFull, // *
    Big,     // O
    Middle,  // o
    Small,   // .
}

pub const SCROLLBAR_SPACE: i16 = 5;

/// How many dots at most will there be
const MAX_DOTS: usize = 5;

impl ScrollBar {
    /// Maximum size (width/height) of a dot
    pub const MAX_DOT_SIZE: i16 = 5;
    /// Distance between two dots
    pub const DOTS_DISTANCE: i16 = 2;
    pub const DOTS_INTERVAL: i16 = Self::MAX_DOT_SIZE + Self::DOTS_DISTANCE;
    pub const MAX_WIDTH: i16 = Self::dots_width(MAX_DOTS);

    pub fn new(page_count: usize) -> Self {
        Self {
            pad: Pad::with_background(theme::BG),
            page_count,
            active_page: 0,
        }
    }

    /// Page count will be given later as it is not available yet.
    pub fn to_be_filled_later() -> Self {
        Self::new(0)
    }

    pub const fn dots_width(dots_shown: usize) -> i16 {
        Self::DOTS_INTERVAL * dots_shown as i16 - Self::DOTS_DISTANCE
    }

    /// The width the scrollbar will really occupy.
    pub fn overall_width(&self) -> i16 {
        let dots_shown = self.page_count.min(MAX_DOTS);
        Self::dots_width(dots_shown)
    }

    pub fn set_page_count(&mut self, page_count: usize) {
        self.page_count = page_count;
    }

    /// Create a (seemingly circular) dot given its top left point.
    /// Make it full when it is active, otherwise paint just the perimeter and
    /// leave center empty.
    fn render_dot<'s>(&self, target: &mut impl Renderer<'s>, dot_type: &DotType, top_right: Point) {
        let full_square =
            Rect::from_top_right_and_size(top_right, Offset::uniform(Self::MAX_DOT_SIZE));

        match dot_type {
            DotType::BigFull => shape::Bar::new(full_square)
                .with_radius(2)
                .with_bg(theme::FG)
                .render(target),

            DotType::Big => shape::Bar::new(full_square)
                .with_radius(2)
                .with_fg(theme::FG)
                .render(target),

            DotType::Middle => shape::Bar::new(full_square.shrink(1))
                .with_radius(1)
                .with_fg(theme::FG)
                .render(target),

            DotType::Small => shape::Bar::new(full_square.shrink(2))
                .with_bg(theme::FG)
                .render(target),
        }
    }

    /// Get a sequence of dots to be drawn, with specifying their appearance.
    /// Painting only big dots in case of 2 and 3 pages,
    /// three big and 1 middle in case of 4 pages,
    /// and three big, one middle and one small in case of 5 and more pages.
    fn get_drawable_dots(&self) -> Vec<DotType, MAX_DOTS> {
        let mut dots = Vec::new();

        match self.page_count {
            0..=3 => {
                // *OO
                // O*O
                // OO*
                for i in 0..self.page_count {
                    if i == self.active_page {
                        unwrap!(dots.push(DotType::BigFull));
                    } else {
                        unwrap!(dots.push(DotType::Big));
                    }
                }
            }
            4 => {
                // *OOo
                // O*Oo
                // oO*O
                // oOO*
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
                // *OOo.
                // O*Oo.
                // oO*Oo
                // ...
                // oO*Oo
                // .oO*O
                // .oOO*
                let full_dot_index = match self.active_page {
                    0 => 0,
                    1 => 1,
                    last_but_one if last_but_one == self.page_count - 2 => 3,
                    last if last == self.page_count - 1 => 4,
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

    fn render_horizontal<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let mut top_right = self.pad.area.top_right();
        for dot in self.get_drawable_dots().iter().rev() {
            self.render_dot(target, dot, top_right);
            top_right.x -= Self::DOTS_INTERVAL;
        }
    }
}

impl Component for ScrollBar {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        // Occupying as little space as possible (according to the number of pages),
        // aligning to the right.
        let scrollbar_area = Rect::from_top_right_and_size(
            bounds.top_right() + Offset::y(1), // offset for centering vertically
            Offset::new(self.overall_width(), Self::MAX_DOT_SIZE),
        );
        self.pad.place(scrollbar_area);
        scrollbar_area
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    /// Displaying one dot for each page.
    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        // Not showing the scrollbar dot when there is only one page
        if self.page_count <= 1 {
            return;
        }

        self.pad.render(target);
        self.render_horizontal(target);
    }
}

impl Paginate for ScrollBar {
    fn page_count(&self) -> usize {
        self.page_count
    }

    fn change_page(&mut self, active_page: usize) {
        self.active_page = active_page;
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for ScrollBar {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ScrollBar");
        t.int("scrollbar_page_count", self.page_count as i64);
        t.int("scrollbar_active_page", self.active_page as i64);
    }
}
