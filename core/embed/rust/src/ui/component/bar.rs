use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    display,
    display::Color,
    geometry::Rect,
    shape,
    shape::Renderer,
};

pub struct Bar {
    area: Rect,
    color: Color,
    bg_color: Color,
    radius: i16,
}

impl Bar {
    pub fn new(color: Color, bg_color: Color, radius: i16) -> Self {
        Self {
            area: Rect::zero(),
            color,
            bg_color,
            radius,
        }
    }
}

impl Component for Bar {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.area
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        display::rect_fill_rounded(self.area, self.color, self.bg_color, self.radius as u8);
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        shape::Bar::new(self.area)
            .with_bg(self.color)
            .with_radius(self.radius)
            .render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Bar {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Bar");
    }
}
