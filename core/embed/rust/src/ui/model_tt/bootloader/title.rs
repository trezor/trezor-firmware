use crate::ui::geometry::Point;
use crate::ui::model_tt::bootloader::theme::{BLD_BG, BLD_TITLE_COLOR};
use crate::ui::model_tt::theme::FONT_BOLD;
use crate::ui::{
    component::{Component, Event, EventCtx},
    display,
    geometry::Rect,
};

pub enum TitleMsg {
    None,
}

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
    type Msg = TitleMsg;

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
            FONT_BOLD,
            BLD_TITLE_COLOR,
            BLD_BG,
        );
        display::text_top_left(
            Point::new(self.area.top_left().x + 115, self.area.top_left().y),
            self.version,
            FONT_BOLD,
            BLD_TITLE_COLOR,
            BLD_BG,
        );
    }

    fn bounds(&self, _sink: &mut dyn FnMut(Rect)) {}
}
