use crate::{
    trezorhal::display::{image, ToifFormat},
    ui::{
        component::{Component, Event, EventCtx, Never},
        display,
        display::{toif::Toif, Color, Icon},
        geometry::{Alignment2D, Offset, Point, Rect, CENTER},
    },
};

#[derive(PartialEq, Eq, Clone, Copy)]
pub struct Image {
    pub toif: Toif,
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
        image(r.x0, r.y0, r.width(), r.height(), self.toif.zdata());
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
        self.draw(self.area.center(), CENTER);
    }

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
        t.open("Image");
        t.close();
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
        self.bg_top_left = self.bg.toif.size().snap(bounds.center(), CENTER);

        let ft_top_left = self.fg.toif.size().snap(bounds.center(), CENTER);
        self.fg_offset = ft_top_left - self.bg_top_left;

        Rect::from_top_left_and_size(self.bg_top_left, self.bg.toif.size())
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        self.paint_image();
    }

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
        t.open("BlendedImage");
        t.close();
    }
}
