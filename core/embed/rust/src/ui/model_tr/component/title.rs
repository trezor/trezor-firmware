use crate::{
    micropython::buffer::StrBuffer,
    time::Instant,
    ui::{
        component::{Component, Event, EventCtx, Marquee, Never},
        display,
        geometry::{Offset, Rect},
        model_tr::theme,
    },
};

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
            title,
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

    /// Display title/header at the top left of the given area.
    /// Returning the painted height of the whole header.
    pub fn paint_header_left(title: StrBuffer, area: Rect) -> i16 {
        let text_height = theme::FONT_HEADER.text_height();
        let title_baseline = area.top_left() + Offset::y(text_height - 1);
        display::text_left(
            title_baseline,
            title.as_ref(),
            theme::FONT_HEADER,
            theme::FG,
            theme::BG,
        );
        text_height
    }

    /// Display title/header centered at the top of the given area.
    /// Returning the painted height of the whole header.
    pub fn paint_header_centered(title: StrBuffer, area: Rect) -> i16 {
        let text_height = theme::FONT_HEADER.text_height();
        let title_baseline = area.top_center() + Offset::y(text_height - 1);
        display::text_center(
            title_baseline,
            title.as_ref(),
            theme::FONT_HEADER,
            theme::FG,
            theme::BG,
        );
        text_height
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
            Self::paint_header_centered(self.title, self.area);
        } else {
            Self::paint_header_left(self.title, self.area);
        }
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Title {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Title");
        t.title(self.title.as_ref());
        t.close();
    }
}
