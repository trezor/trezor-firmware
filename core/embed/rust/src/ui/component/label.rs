use crate::{
    strutil::TString,
    ui::{
        component::{Component, Event, EventCtx, Never},
        display::Font,
        geometry::{Alignment, Insets, Offset, Point, Rect},
        shape::Renderer,
    },
};

use super::{text::TextStyle, TextLayout};

#[derive(Clone)]
pub struct Label<'a> {
    text: TString<'a>,
    layout: TextLayout,
    vertical: Alignment,
}

impl<'a> Label<'a> {
    pub const fn new(text: TString<'a>, align: Alignment, style: TextStyle) -> Self {
        Self {
            text,
            layout: TextLayout::new(style).with_align(align),
            vertical: Alignment::Start,
        }
    }

    pub const fn left_aligned(text: TString<'a>, style: TextStyle) -> Self {
        Self::new(text, Alignment::Start, style)
    }

    pub const fn right_aligned(text: TString<'a>, style: TextStyle) -> Self {
        Self::new(text, Alignment::End, style)
    }

    pub const fn centered(text: TString<'a>, style: TextStyle) -> Self {
        Self::new(text, Alignment::Center, style)
    }

    pub const fn top_aligned(mut self) -> Self {
        self.vertical = Alignment::Start;
        self
    }

    pub const fn vertically_centered(mut self) -> Self {
        self.vertical = Alignment::Center;
        self
    }

    pub const fn bottom_aligned(mut self) -> Self {
        self.vertical = Alignment::End;
        self
    }

    pub const fn styled(mut self, style: TextStyle) -> Self {
        self.layout.style = style;
        self
    }

    pub fn text(&self) -> &TString<'a> {
        &self.text
    }

    pub fn set_text(&mut self, text: TString<'a>) {
        self.text = text;
    }

    pub fn set_style(&mut self, style: TextStyle) {
        self.layout.style = style;
    }

    pub fn font(&self) -> Font {
        self.layout.style.text_font
    }

    pub fn area(&self) -> Rect {
        self.layout.bounds
    }

    pub const fn alignment(&self) -> Alignment {
        self.layout.align
    }

    pub fn max_size(&self) -> Offset {
        let font = self.font();
        let width = self.text.map(|c| font.text_width(c));
        Offset::new(width, font.text_max_height())
    }

    pub fn text_height(&self, width: i16) -> i16 {
        let bounds = Rect::from_top_left_and_size(Point::zero(), Offset::new(width, i16::MAX));

        self.text
            .map(|c| self.layout.with_bounds(bounds).fit_text(c).height())
    }

    pub fn text_area(&self) -> Rect {
        // XXX only works on single-line labels
        let available_width = self.layout.bounds.width();
        let width = self.text.map(|c| self.font().text_width(c));
        let height = self.font().text_height();
        let cursor = self.layout.initial_cursor();
        let baseline = match self.alignment() {
            Alignment::Start => cursor,
            Alignment::Center => cursor + Offset::x(available_width / 2) - Offset::x(width / 2),
            Alignment::End => cursor + Offset::x(available_width) - Offset::x(width),
        };
        Rect::from_bottom_left_and_size(baseline, Offset::new(width, height))
    }

    pub fn render_with_alpha<'s>(&self, target: &mut impl Renderer<'s>, alpha: u8) {
        self.text
            .map(|c| self.layout.render_text_with_alpha(c, target, alpha));
    }
}

impl Component for Label<'_> {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        let height = self
            .text
            .map(|c| self.layout.with_bounds(bounds).fit_text(c).height());
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

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.text.map(|c| self.layout.render_text(c, target));
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Label<'_> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Label");
        t.string("text", self.text);
    }
}
