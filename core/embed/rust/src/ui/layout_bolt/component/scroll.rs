use crate::ui::{
    component::{Component, Event, EventCtx, Never, Paginate},
    display::toif::Icon,
    geometry::{Alignment2D, Axis, LinearPlacement, Offset, Rect},
    shape::{self, Renderer},
    util::Pager,
};

use super::theme;

pub struct ScrollBar {
    area: Rect,
    layout: LinearPlacement,
    pager: Pager,
}

impl ScrollBar {
    pub const DOT_SIZE: i16 = 8;
    /// If there's more pages than this value then smaller dots are used at the
    /// beginning/end of the scrollbar to denote the fact.
    const MAX_DOTS: u16 = 7;
    /// Center to center.
    const DOT_INTERVAL: i16 = 18;

    pub fn new(axis: Axis) -> Self {
        let layout = LinearPlacement::new(axis);
        Self {
            area: Rect::zero(),
            layout: layout.align_at_center().with_spacing(Self::DOT_INTERVAL),
            pager: Pager::default(),
        }
    }

    pub fn vertical() -> Self {
        Self::new(Axis::Vertical)
    }

    pub fn horizontal() -> Self {
        Self::new(Axis::Horizontal)
    }

    pub fn set_pager(&mut self, pager: Pager) {
        self.pager = pager
    }

    pub fn has_next_page(&self) -> bool {
        self.pager.has_next()
    }

    pub fn has_previous_page(&self) -> bool {
        self.pager.has_prev()
    }

    pub fn go_to_relative(&mut self, step: isize) {
        let current = self.pager.current() as isize;
        let total = self.pager.total() as isize;
        let new_page = (current + step).clamp(0, total - 1) as u16;
        self.change_page(new_page);
    }
}

impl Component for ScrollBar {
    type Msg = Never;

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        fn dotsize(distance: u16, nhidden: u16) -> Icon {
            match (nhidden.saturating_sub(distance)).min(2 - distance) {
                0 => theme::DOT_INACTIVE,
                1 => theme::DOT_INACTIVE_HALF,
                _ => theme::DOT_INACTIVE_QUARTER,
            }
        }

        // Number of visible dots.
        let num_shown = self.pager.total().min(Self::MAX_DOTS);
        // Page indices corresponding to the first (and last) dot.
        let first_shown = self
            .pager
            .current()
            .saturating_sub(Self::MAX_DOTS / 2)
            .min(self.pager().total().saturating_sub(Self::MAX_DOTS));
        let last_shown = first_shown + num_shown - 1;

        let mut cursor = self.area.center()
            - Offset::on_axis(
                self.layout.axis,
                Self::DOT_INTERVAL * (num_shown.saturating_sub(1) as i16) / 2,
            );
        for i in first_shown..(last_shown + 1) {
            let icon = if i == self.pager.current() {
                theme::DOT_ACTIVE
            } else if i <= first_shown + 1 {
                let before_first_shown = first_shown;
                dotsize(i - first_shown, before_first_shown)
            } else if i >= last_shown - 1 {
                let after_last_shown = self.pager.last() - last_shown;
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

impl Paginate for ScrollBar {
    fn pager(&self) -> Pager {
        self.pager
    }

    fn change_page(&mut self, active_page: u16) {
        self.pager.set_current(active_page);
    }
}
