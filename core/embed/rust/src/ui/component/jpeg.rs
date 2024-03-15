use crate::error::Error;
use crate::micropython::{buffer::get_buffer, obj::Obj};

use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    display,
    geometry::{Alignment2D, Offset, Rect},
    shape,
    shape::Renderer,
};

pub enum ImageBuffer {
    Object { obj: Obj },
    Slice { data: &'static [u8] },
}

impl ImageBuffer {
    pub fn from_object(obj: Obj) -> Result<Self, Error> {
        if !obj.is_bytes() {
            return Err(Error::TypeError);
        }
        Ok(ImageBuffer::Object { obj })
    }

    pub fn from_slice(data: &'static [u8]) -> Self {
        ImageBuffer::Slice { data }
    }

    pub fn is_empty(&self) -> bool {
        self.data().is_empty()
    }

    pub fn data(&self) -> &[u8] {
        match self {
            // SAFETY: We expect no existing mutable reference. Resulting reference is
            // discarded before returning to micropython.
            ImageBuffer::Object { obj } => unsafe { unwrap!(get_buffer(*obj)) },
            ImageBuffer::Slice { data } => data,
        }
    }
}

pub struct Jpeg {
    area: Rect,
    data: ImageBuffer,
    scale: u8,
}

impl Jpeg {
    pub fn new(data: ImageBuffer, scale: u8) -> Self {
        Self {
            area: Rect::zero(),
            data,
            scale,
        }
    }
}

impl Component for Jpeg {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.area
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        if let Some((size, _)) = display::tjpgd::jpeg_info(self.data.data()) {
            let off = Offset::new(size.x / (2 << self.scale), size.y / (2 << self.scale));
            display::tjpgd::jpeg(self.data.data(), self.area.center() - off, self.scale);
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        shape::JpegImage::new(self.area.center(), self.data.data())
            .with_align(Alignment2D::CENTER)
            .with_scale(self.scale)
            .render(target);
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area)
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Jpeg {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Jpeg");
    }
}
