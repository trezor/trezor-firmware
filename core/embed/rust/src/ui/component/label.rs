use crate::{
    strutil::TString,
    ui::{
        component::{text::layout::LayoutFit, Component, Event, EventCtx, Never},
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
    must_fit: bool,
}

impl<'a> Label<'a> {
    pub const fn new(text: TString<'a>, align: Alignment, style: TextStyle) -> Self {
        Self {
            text,
            layout: TextLayout::new(style).with_align(align),
            vertical: Alignment::Start,
            must_fit: true,
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

    pub const fn must_fit(mut self, must_fit: bool) -> Self {
        self.must_fit = must_fit;
        self
    }

    pub fn text(&self) -> &TString<'a> {
        &self.text
    }

    pub fn style(&self) -> &TextStyle {
        &self.layout.style
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

    pub fn text_height(&self, width: i16) -> i16 {
        let bounds = Rect::from_top_left_and_size(Point::zero(), Offset::new(width, i16::MAX));
        let layout_fit = self
            .text
            .map(|c| self.layout.with_bounds(bounds).fit_text(c));
        debug_assert!(matches!(layout_fit, LayoutFit::Fitting { .. }));
        layout_fit.height()
    }

    pub fn render_with_alpha<'s>(&self, target: &mut impl Renderer<'s>, alpha: u8) {
        self.text.map(|c| {
            self.layout
                .render_text_with_alpha(c, target, alpha, self.must_fit)
        });
    }
}

impl Component for Label<'_> {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        let layout_fit = self
            .text
            .map(|c| self.layout.with_bounds(bounds).fit_text(c));
        debug_assert!(matches!(layout_fit, LayoutFit::Fitting { .. }));
        let diff = (bounds.height() - layout_fit.height()).max(0);
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
        self.text.map(|c| self.layout.render_text(c, target, true));
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Label<'_> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Label");
        t.string("text", self.text);
    }
}
