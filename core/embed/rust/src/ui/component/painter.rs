#[cfg(feature = "jpeg")]
use crate::ui::geometry::Offset;
use crate::ui::{
    component::{image::Image, Component, Event, EventCtx, Never},
    display,
    geometry::{Rect, CENTER},
};

pub struct Painter<F> {
    area: Rect,
    func: F,
}

impl<F> Painter<F> {
    pub fn new(func: F) -> Self {
        Self {
            func,
            area: Rect::zero(),
        }
    }
}

impl<F> Component for Painter<F>
where
    F: FnMut(Rect),
{
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.area
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        (self.func)(self.area);
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area)
    }
}

#[cfg(feature = "ui_debug")]
impl<F> crate::trace::Trace for Painter<F> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.string("Painter")
    }
}

pub fn qrcode_painter<T>(data: T, max_size: u32, case_sensitive: bool) -> Painter<impl FnMut(Rect)>
where
    T: AsRef<str>,
{
    // Ignore errors as we currently can't propagate them out of paint().
    let f = move |area: Rect| {
        display::qrcode(area.center(), data.as_ref(), max_size, case_sensitive).unwrap_or(())
    };
    Painter::new(f)
}

pub fn image_painter(image: Image) -> Painter<impl FnMut(Rect)> {
    let f = move |area: Rect| image.draw(area.center(), CENTER);
    Painter::new(f)
}

#[cfg(feature = "jpeg")]
pub fn jpeg_painter<'a>(
    image: impl Fn() -> &'a [u8],
    size: Offset,
    scale: u8,
) -> Painter<impl FnMut(Rect)> {
    let off = Offset::new(size.x / (2 << scale), size.y / (2 << scale));
    let f = move |area: Rect| display::tjpgd::jpeg(image(), area.center() - off, scale);
    Painter::new(f)
}
