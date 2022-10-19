use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    display::{self, Font},
    geometry::{Point, Rect},
    model_tr::bootloader::theme::{BLD_BG, BLD_FG},
};

pub struct Title {
    version: &'static str,
    area: Rect,
}

impl Title {
    pub fn new(version: &'static str) -> Self {
        Self {
            version,
            area: Rect::zero(),
        }
    }
}

impl Component for Title {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        display::text_top_left(
            self.area.top_left(),
            "BOOTLOADER",
            Font::NORMAL,
            BLD_FG,
            BLD_BG,
        );
        display::text_top_left(
            Point::new(self.area.top_left().x + 65, self.area.top_left().y),
            self.version,
            Font::NORMAL,
            BLD_FG,
            BLD_BG,
        );
    }

    fn bounds(&self, _sink: &mut dyn FnMut(Rect)) {}
}
