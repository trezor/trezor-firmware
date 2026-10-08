use super::super::theme;
use crate::strutil::ShortString;
use crate::ui::component::{Component, Event, EventCtx, Never, Pad, Paginate};
use crate::ui::geometry::{Alignment, Alignment2D, Offset, Point, Rect};
use crate::ui::shape::{self, Renderer};
use crate::ui::util::Pager;

/// Numeric "current/total" page counter to be painted at the top right of the
/// screen.
pub struct ScrollBar {
    pad: Pad,
    pager: Pager,
}

pub const SCROLLBAR_SPACE: i16 = 5;

impl ScrollBar {
    /// Space the separator icon takes (with a 1px gap on both sides).
    const SEPARATOR_WIDTH: i16 = theme::ICON_PAGE_SEPARATOR.toif.width() + 2;

    pub fn new(page_count: u16) -> Self {
        Self {
            pad: Pad::with_background(theme::BG),
            pager: Pager::new(page_count),
        }
    }

    /// Page count will be given later as it is not available yet.
    pub fn to_be_filled_later() -> Self {
        Self::new(1)
    }

    /// The width the scrollbar will really occupy.
    pub fn overall_width(&self) -> i16 {
        // Reserving the same width for the current page as for the total,
        // so that the counter fits on every page.
        let (_, total) = self.texts();
        2 * theme::FONT_HEADER.text_width(&total) + Self::SEPARATOR_WIDTH
    }

    /// The height the scrollbar will really occupy.
    pub fn overall_height(&self) -> i16 {
        theme::FONT_HEADER.text_height()
    }

    pub fn set_pager(&mut self, pager: Pager) {
        self.pager = pager;
    }

    fn texts(&self) -> (ShortString, ShortString) {
        (
            uformat!("{}", self.pager.current() + 1),
            uformat!("{}", self.pager.total()),
        )
    }
}

impl Component for ScrollBar {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        // Occupying as little space as possible (according to the number of pages),
        // aligning to the right.
        let scrollbar_area = Rect::from_top_right_and_size(
            bounds.top_right(),
            Offset::new(self.overall_width(), self.overall_height()),
        );
        self.pad.place(scrollbar_area);
        scrollbar_area
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    /// Displaying the "current/total" counter, right-aligned.
    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        // Not showing the counter when there is only one page
        if self.pager.is_single() {
            return;
        }

        self.pad.render(target);

        let (current, total) = self.texts();
        let font = theme::FONT_HEADER;
        let baseline = self.pad.area.top_right() + Offset::y(font.text_height() - 1);
        let current_right = baseline.x - font.text_width(&total) - Self::SEPARATOR_WIDTH;
        shape::Text::new(baseline, &total, font)
            .with_align(Alignment::End)
            .with_fg(theme::FG)
            .render(target);
        shape::ToifImage::new(
            Point::new(current_right + 1, baseline.y),
            theme::ICON_PAGE_SEPARATOR.toif,
        )
        .with_align(Alignment2D::BOTTOM_LEFT)
        .with_fg(theme::FG)
        .render(target);
        shape::Text::new(Point::new(current_right, baseline.y), &current, font)
            .with_align(Alignment::End)
            .with_fg(theme::FG)
            .render(target);
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

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for ScrollBar {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ScrollBar");
        t.int("scrollbar_page_count", i64::from(self.pager.total()));
        t.int("scrollbar_active_page", i64::from(self.pager.current()));
    }
}
