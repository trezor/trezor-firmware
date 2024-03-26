use crate::{
    strutil::TString,
    ui::{
        component::{Component, Event, EventCtx, Never},
        display::Font,
        geometry::{Alignment, Insets, Offset, Point, Rect},
    },
};

use super::{text::TextStyle, TextLayout};

pub struct Label<'a> {
    text: TString<'a>,
    layout: TextLayout,
    vertical: Alignment,
}

impl<'a> Label<'a> {
    pub fn new(text: TString<'a>, align: Alignment, style: TextStyle) -> Self {
        Self {
            text,
            layout: TextLayout::new(style).with_align(align),
            vertical: Alignment::Start,
        }
    }

    pub fn left_aligned(text: TString<'a>, style: TextStyle) -> Self {
        Self::new(text, Alignment::Start, style)
    }

    pub fn right_aligned(text: TString<'a>, style: TextStyle) -> Self {
        Self::new(text, Alignment::End, style)
    }

    pub fn centered(text: TString<'a>, style: TextStyle) -> Self {
        Self::new(text, Alignment::Center, style)
    }

    pub fn vertically_centered(mut self) -> Self {
        self.vertical = Alignment::Center;
        self
    }

    pub fn text(&self) -> &TString<'a> {
        &self.text
    }

    pub fn set_text(&mut self, text: TString<'a>) {
        self.text = text;
    }

    pub fn font(&self) -> Font {
        self.layout.style.text_font
    }

    pub fn area(&self) -> Rect {
        self.layout.bounds
    }

    pub fn alignment(&self) -> Alignment {
        self.layout.align
    }

    pub fn max_size(&self) -> Offset {
        let font = self.font();
        Offset::new(
            font.text_width(self.text.map(|c| c)),
            font.text_max_height(),
        )
    }

    pub fn text_height(&self, width: i16) -> i16 {
        let bounds = Rect::from_top_left_and_size(Point::zero(), Offset::new(width, i16::MAX));
        self.layout
            .with_bounds(bounds)
            .fit_text(self.text.map(|c| c))
            .height()
    }

    pub fn text_area(&self) -> Rect {
        // XXX only works on single-line labels
        assert!(self.layout.bounds.height() <= self.font().text_max_height());
        let available_width = self.layout.bounds.width();
        let width = self.font().text_width(self.text.map(|c| c));
        let height = self.font().text_height();
        let cursor = self.layout.initial_cursor();
        let baseline = match self.alignment() {
            Alignment::Start => cursor,
            Alignment::Center => cursor + Offset::x(available_width / 2) - Offset::x(width / 2),
            Alignment::End => cursor + Offset::x(available_width) - Offset::x(width),
        };
        Rect::from_bottom_left_and_size(baseline, Offset::new(width, height))
    }
}

impl Component for Label<'_> {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        let height = self
            .layout
            .with_bounds(bounds)
            .fit_text(self.text.map(|c| c))
            .height();
        let diff = bounds.height() - height;
        let insets = match self.vertical {
            Alignment::Start => Insets::bottom(diff),
            Alignment::Center => Insets::new(diff / 2, 0, diff / 2 + diff % 2, 0),
            Alignment::End => Insets::top(diff),
        };
        self.layout.bounds = bounds.inset(insets);
        self.layout.bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        self.layout.render_text(self.text.map(|c| c));
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.layout.bounds)
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Label<'_> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Label");
        t.string("text", self.text.map(|c| c).into());
    }
}
