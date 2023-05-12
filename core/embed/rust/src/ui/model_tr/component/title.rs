use crate::{
    micropython::buffer::StrBuffer,
    time::Instant,
    ui::{
        component::{Component, Event, EventCtx, Marquee, Never},
        display,
        geometry::{Offset, Rect},
    },
};

use super::super::theme;

pub struct Title {
    area: Rect,
    title: StrBuffer,
    marquee: Marquee<StrBuffer>,
    needs_marquee: bool,
    centered: bool,
}

impl Title {
    pub fn new(title: StrBuffer) -> Self {
        Self {
            title: title.clone(),
            marquee: Marquee::new(title, theme::FONT_HEADER, theme::FG, theme::BG),
            needs_marquee: false,
            area: Rect::zero(),
            centered: false,
        }
    }

    pub fn with_centered(mut self) -> Self {
        self.centered = true;
        self
    }

    pub fn get_text(&self) -> &str {
        self.title.as_ref()
    }

    pub fn set_text(&mut self, ctx: &mut EventCtx, new_text: StrBuffer) {
        self.title = new_text.clone();
        self.marquee.set_text(self.title.clone());
        let text_width = theme::FONT_HEADER.text_width(new_text.as_ref());
        self.needs_marquee = text_width > self.area.width();
        // Resetting the marquee to the beginning and starting it when necessary.
        self.marquee.reset();
        if self.needs_marquee {
            self.marquee.start(ctx, Instant::now());
        }
    }

    /// Display title/header at the top left of the given area.
    pub fn paint_header_left(title: &StrBuffer, area: Rect) {
        let text_height = theme::FONT_HEADER.text_height();
        let title_baseline = area.top_left() + Offset::y(text_height - 1);
        display::text_left(
            title_baseline,
            title.as_ref(),
            theme::FONT_HEADER,
            theme::FG,
            theme::BG,
        );
    }

    /// Display title/header centered at the top of the given area.
    pub fn paint_header_centered(title: &StrBuffer, area: Rect) {
        let text_height = theme::FONT_HEADER.text_height();
        let title_baseline = area.top_center() + Offset::y(text_height - 1);
        display::text_center(
            title_baseline,
            title.as_ref(),
            theme::FONT_HEADER,
            theme::FG,
            theme::BG,
        );
    }
}

impl Component for Title {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.marquee.place(bounds);
        let width = theme::FONT_HEADER.text_width(self.title.as_ref());
        self.needs_marquee = width > self.area.width();
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if self.needs_marquee {
            if !self.marquee.is_animating() {
                self.marquee.start(ctx, Instant::now());
            }
            return self.marquee.event(ctx, event);
        }
        None
    }

    fn paint(&mut self) {
        if self.needs_marquee {
            self.marquee.paint();
        } else if self.centered {
            Self::paint_header_centered(&self.title, self.area);
        } else {
            Self::paint_header_left(&self.title, self.area);
        }
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Title {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Title");
        t.string("text", self.title.as_ref());
    }
}
