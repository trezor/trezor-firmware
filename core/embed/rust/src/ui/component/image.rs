use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    display,
    display::{
        toif::{image, Toif, ToifFormat},
        Color, Icon,
    },
    geometry::{Alignment2D, Offset, Point, Rect},
};

#[derive(PartialEq, Eq, Clone, Copy)]
pub struct Image {
    pub toif: Toif<'static>,
    area: Rect,
}

impl Image {
    pub fn new(data: &'static [u8]) -> Self {
        let toif = unwrap!(Toif::new(data));
        assert!(toif.format() == ToifFormat::FullColorLE);
        Self {
            toif,
            area: Rect::zero(),
        }
    }

    /// Display the icon with baseline Point, aligned according to the
    /// `alignment` argument.
    pub fn draw(&self, baseline: Point, alignment: Alignment2D) {
        let r = Rect::snap(baseline, self.toif.size(), alignment);
        image(self, r.center());
    }
}

impl Component for Image {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.area
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        self.draw(self.area.center(), Alignment2D::CENTER);
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(Rect::from_center_and_size(
            self.area.center(),
            self.toif.size(),
        ));
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Image {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Image");
    }
}

pub struct BlendedImage {
    bg: Icon,
    fg: Icon,
    bg_color: Color,
    fg_color: Color,
    area_color: Color,
    bg_top_left: Point,
    fg_offset: Offset,
}

impl BlendedImage {
    pub fn new(bg: Icon, fg: Icon, bg_color: Color, fg_color: Color, area_color: Color) -> Self {
        Self {
            bg,
            fg,
            bg_color,
            fg_color,
            area_color,
            bg_top_left: Point::zero(),
            fg_offset: Offset::zero(),
        }
    }

    // NOTE: currently this function is used too rarely to justify writing special
    // case for unblended image.
    pub fn single(icon: Icon, color: Color, area_color: Color) -> Self {
        Self::new(icon, icon, color, color, area_color)
    }

    fn paint_image(&self) {
        display::icon_over_icon(
            None,
            (self.bg, self.bg_top_left.into(), self.bg_color),
            (self.fg, self.fg_offset, self.fg_color),
            self.area_color,
        );
    }
}

impl Component for BlendedImage {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg_top_left = self
            .bg
            .toif
            .size()
            .snap(bounds.center(), Alignment2D::CENTER);
        let ft_top_left = self
            .fg
            .toif
            .size()
            .snap(bounds.center(), Alignment2D::CENTER);
        self.fg_offset = ft_top_left - self.bg_top_left;

        Rect::from_top_left_and_size(self.bg_top_left, self.bg.toif.size())
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        self.paint_image();
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(Rect::from_top_left_and_size(
            self.bg_top_left,
            self.bg.toif.size(),
        ));
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for BlendedImage {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("BlendedImage");
    }
}
