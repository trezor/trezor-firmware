use crate::{
    io::BinaryData,
    ui::{
        component::{Component, Event, EventCtx, Never},
        display::image::ImageInfo,
        geometry::{Offset, Point, Rect},
        shape,
        shape::{render_on_canvas, ImageBuffer, Renderer, Rgb565Canvas},
    },
};

pub struct CachedJpeg {
    area: Rect,
    image_size: Offset,
    jpeg: ImageBuffer<Rgb565Canvas<'static>>,
    scale: u8,
}

impl CachedJpeg {
    pub fn new(image: BinaryData<'static>, scale: u8) -> Self {
        let size = match ImageInfo::parse(image) {
            ImageInfo::Jpeg(info) => {
                if info.mcu_height() > 16 {
                    Offset::zero()
                } else {
                    Offset::new(info.width(), info.height())
                }
            }
            _ => Offset::zero(),
        };

        let mut buf = unwrap!(ImageBuffer::new(size), "no image buf");

        render_on_canvas(buf.canvas(), None, |target| {
            shape::JpegImage::new_image(Point::zero(), image)
                .with_scale(scale)
                .render(target);
        });

        Self {
            area: Rect::zero(),
            image_size: size,
            jpeg: buf,
            scale,
        }
    }
}

impl Component for CachedJpeg {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.area
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {}

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let off = Offset::new(
            self.image_size.x / (2 << self.scale),
            self.image_size.y / (2 << self.scale),
        );
        let pos = self.area.center() - off;

        shape::RawImage::new(
            Rect::from_top_left_and_size(pos, self.image_size * (1.0 / (1 << self.scale) as f32)),
            self.jpeg.view(),
        )
        .render(target);
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area)
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for CachedJpeg {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("CachedJpeg");
    }
}

#[cfg(feature = "micropython")]
mod micropython {
    use crate::{error::Error, micropython::obj::Obj, ui::layout::obj::ComponentMsgObj};
    impl ComponentMsgObj for super::CachedJpeg {
        fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
            unreachable!();
        }
    }
}
