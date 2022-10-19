use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    display,
    display::{toif_info, Color},
    geometry::{Alignment, Offset, Point, Rect},
};

pub struct Image {
    image: &'static [u8],
    area: Rect,
}

impl Image {
    pub fn new(image: &'static [u8]) -> Self {
        Self {
            image,
            area: Rect::zero(),
        }
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
        display::image(self.area.center(), self.image)
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        if let Some((size, _)) = display::toif_info(self.image) {
            sink(Rect::from_center_and_size(self.area.center(), size));
        }
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
    bg: &'static [u8],
    fg: &'static [u8],
    bg_color: Color,
    fg_color: Color,
    area_color: Color,
    bg_top_left: Point,
    fg_offset: Offset,
}

impl BlendedImage {
    pub fn new(
        bg: &'static [u8],
        fg: &'static [u8],
        bg_color: Color,
        fg_color: Color,
        area_color: Color,
    ) -> Self {
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

    #[cfg(feature = "dma2d")]
    fn paint_image(&self) {
        display::icon_over_icon(
            None,
            (self.bg, self.bg_top_left.into(), self.bg_color),
            (self.fg, self.fg_offset, self.fg_color),
            self.area_color,
        );
    }

    #[cfg(not(feature = "dma2d"))]
    fn paint_image(&self) {
        display::icon_top_left(self.bg_top_left, self.bg, self.bg_color, self.area_color);
        display::icon_top_left(
            self.bg_top_left + self.fg_offset,
            self.fg,
            self.fg_color,
            self.bg_color,
        );
    }
}

impl Component for BlendedImage {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (bg_size, _) = unwrap!(toif_info(self.bg));

        self.bg_top_left = bg_size.snap(bounds.center(), Alignment::Center, Alignment::Center);

        if let Some((fg_size, _)) = toif_info(self.fg) {
            let ft_top_left = fg_size.snap(bounds.center(), Alignment::Center, Alignment::Center);
            self.fg_offset = ft_top_left - self.bg_top_left;
        }
        Rect::from_top_left_and_size(self.bg_top_left, bg_size)
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        self.paint_image();
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        if let Some((size, _)) = display::toif_info(self.bg) {
            sink(Rect::from_top_left_and_size(self.bg_top_left, size));
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for BlendedImage {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("BlendedImage");
        t.close();
    }
}
