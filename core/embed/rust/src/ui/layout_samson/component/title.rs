use crate::{
    strutil::TString,
    time::Instant,
    ui::{
        component::{Component, Event, EventCtx, Marquee, Never},
        geometry::{Alignment, Offset, Rect},
        shape,
        shape::Renderer,
    },
};

use super::super::theme;

pub struct Title {
    area: Rect,
    title: TString<'static>,
    marquee: Marquee,
    needs_marquee: bool,
    centered: bool,
}

impl Title {
    pub fn new(title: TString<'static>) -> Self {
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

    pub fn get_text(&self) -> TString {
        self.title
    }

    pub fn set_text(&mut self, ctx: &mut EventCtx, new_text: TString<'static>) {
        self.title = new_text;
        self.marquee.set_text(new_text);
        let text_width = new_text.map(|s| theme::FONT_HEADER.text_width(s));
        self.needs_marquee = text_width > self.area.width();
        // Resetting the marquee to the beginning and starting it when necessary.
        self.marquee.reset();
        if self.needs_marquee {
            self.marquee.start(ctx, Instant::now());
        }
    }

    /// Display title/header at the top left of the given area.
    pub fn render_header_left<'s>(
        target: &mut impl Renderer<'s>,
        title: &TString<'static>,
        area: Rect,
    ) {
        let text_height = theme::FONT_HEADER.text_height();
        let title_baseline = area.top_left() + Offset::y(text_height - 1);
        title.map(|s| {
            shape::Text::new(title_baseline, s)
                .with_font(theme::FONT_HEADER)
                .with_fg(theme::FG)
                .render(target);
        });
    }

    /// Display title/header centered at the top of the given area.
    pub fn render_header_centered<'s>(
        target: &mut impl Renderer<'s>,
        title: &TString<'static>,
        area: Rect,
    ) {
        let text_height = theme::FONT_HEADER.text_height();
        let title_baseline = area.top_center() + Offset::y(text_height - 1);
        title.map(|s| {
            shape::Text::new(title_baseline, s)
                .with_align(Alignment::Center)
                .with_font(theme::FONT_HEADER)
                .with_fg(theme::FG)
                .render(target);
        });
    }
}

impl Component for Title {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.marquee.place(bounds);
        let width = self.title.map(|s| theme::FONT_HEADER.text_width(s));
        self.needs_marquee = width > self.area.width();
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if self.needs_marquee {
            if matches!(event, Event::Attach(_)) {
                self.marquee.start(ctx, Instant::now());
            } else {
                return self.marquee.event(ctx, event);
            }
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if self.needs_marquee {
            self.marquee.render(target);
        } else if self.centered {
            Self::render_header_centered(target, &self.title, self.area);
        } else {
            Self::render_header_left(target, &self.title, self.area);
        }
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Title {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Title");
        t.string("text", self.title);
    }
}
