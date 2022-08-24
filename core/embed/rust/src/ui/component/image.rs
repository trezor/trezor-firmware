use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    display,
    geometry::Rect,
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
