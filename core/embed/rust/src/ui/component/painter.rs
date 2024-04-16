#[cfg(feature = "jpeg")]
use crate::ui::geometry::Offset;
use crate::ui::{
    component::{image::Image, Component, Event, EventCtx, Never},
    display,
    geometry::{Alignment2D, Rect},
    shape,
    shape::Renderer,
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

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let area = self.area;
        shape::Bar::new(area)
            .with_thickness(1)
            .with_fg(display::Color::white())
            .render(target);
        shape::Text::new(area.top_left(), "Paint").render(target); // !@# replace
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area)
    }
}

#[cfg(feature = "ui_debug")]
impl<F> crate::trace::Trace for Painter<F> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Painter");
    }
}

pub fn image_painter(image: Image) -> Painter<impl FnMut(Rect)> {
    let f = move |area: Rect| image.draw(area.center(), Alignment2D::CENTER);
    Painter::new(f)
}

#[cfg(feature = "jpeg")]
pub fn jpeg_painter<'a>(
    image: impl Fn() -> &'a [u8],
    size: Offset,
    scale: u8,
) -> Painter<impl FnMut(Rect)> {
    let off = Offset::new(size.x / (2 << scale), size.y / (2 << scale));
    #[cfg(not(feature = "new_rendering"))]
    let f = move |area: Rect| display::tjpgd::jpeg(image(), area.center() - off, scale);
    #[cfg(feature = "new_rendering")]
    let f = move |area: Rect| {};
    Painter::new(f)
}

pub fn rect_painter(fg: display::Color, bg: display::Color) -> Painter<impl FnMut(Rect)> {
    let f = move |area: Rect| display::rect_fill_rounded(area, fg, bg, 2);
    Painter::new(f)
}
