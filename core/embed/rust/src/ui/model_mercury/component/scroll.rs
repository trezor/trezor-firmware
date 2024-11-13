use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    display::toif::Icon,
    geometry::{Alignment2D, Axis, LinearPlacement, Offset, Rect},
    shape,
    shape::Renderer,
};

use super::theme;

pub struct ScrollBar {
    area: Rect,
    layout: LinearPlacement,
    pub page_count: usize,
    pub active_page: usize,
}

impl ScrollBar {
    pub const DOT_SIZE: i16 = 8;
    /// If there's more pages than this value then smaller dots are used at the
    /// beginning/end of the scrollbar to denote the fact.
    const MAX_DOTS: usize = 7;
    /// Center to center.
    const DOT_INTERVAL: i16 = 18;

    pub fn new(axis: Axis) -> Self {
        let layout = LinearPlacement::new(axis);
        Self {
            area: Rect::zero(),
            layout: layout.align_at_center().with_spacing(Self::DOT_INTERVAL),
            page_count: 0,
            active_page: 0,
        }
    }

    pub fn vertical() -> Self {
        Self::new(Axis::Vertical)
    }

    pub fn horizontal() -> Self {
        Self::new(Axis::Horizontal)
    }

    pub fn set_count_and_active_page(&mut self, page_count: usize, active_page: usize) {
        self.page_count = page_count;
        self.active_page = active_page;
    }

    pub fn has_pages(&self) -> bool {
        self.page_count > 1
    }

    pub fn has_next_page(&self) -> bool {
        self.active_page < self.page_count - 1
    }

    pub fn has_previous_page(&self) -> bool {
        self.active_page > 0
    }

    pub fn go_to_next_page(&mut self) {
        self.go_to_relative(1)
    }

    pub fn go_to_previous_page(&mut self) {
        self.go_to_relative(-1)
    }

    pub fn go_to_relative(&mut self, step: isize) {
        self.go_to(
            (self.active_page as isize + step).clamp(0, self.page_count as isize - 1) as usize,
        );
    }

    pub fn go_to(&mut self, active_page: usize) {
        self.active_page = active_page;
    }
}

impl Component for ScrollBar {
    type Msg = Never;

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        fn dotsize(distance: usize, nhidden: usize) -> Icon {
            match (nhidden.saturating_sub(distance)).min(2 - distance) {
                0 => theme::DOT_INACTIVE,
                1 => theme::DOT_INACTIVE_HALF,
                _ => theme::DOT_INACTIVE_QUARTER,
            }
        }

        // Number of visible dots.
        let num_shown = self.page_count.min(Self::MAX_DOTS);
        // Page indices corresponding to the first (and last) dot.
        let first_shown = self
            .active_page
            .saturating_sub(Self::MAX_DOTS / 2)
            .min(self.page_count.saturating_sub(Self::MAX_DOTS));
        let last_shown = first_shown + num_shown - 1;

        let mut cursor = self.area.center()
            - Offset::on_axis(
                self.layout.axis,
                Self::DOT_INTERVAL * (num_shown.saturating_sub(1) as i16) / 2,
            );
        for i in first_shown..(last_shown + 1) {
            let icon = if i == self.active_page {
                theme::DOT_ACTIVE
            } else if i <= first_shown + 1 {
                let before_first_shown = first_shown;
                dotsize(i - first_shown, before_first_shown)
            } else if i >= last_shown - 1 {
                let after_last_shown = self.page_count - 1 - last_shown;
                dotsize(last_shown - i, after_last_shown)
            } else {
                theme::DOT_INACTIVE
            };
            shape::ToifImage::new(cursor, icon.toif)
                .with_align(Alignment2D::CENTER)
                .with_fg(theme::FG)
                .render(target);
            cursor = cursor + Offset::on_axis(self.layout.axis, Self::DOT_INTERVAL);
        }
    }

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        bounds
    }
}
