use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    constant::WIDTH,
    display::{self, Font},
    geometry::{Offset, Point, Rect},
    model_tr::bootloader::theme::{BLD_BG, BLD_FG, ICON_WARN_TITLE},
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
        display::icon_rust_top_left(Point::new(-1, 0), ICON_WARN_TITLE, BLD_FG, BLD_BG);

        let font = Font::BOLD;
        display::text_center(
            self.area.top_center() + Offset::y(font.text_height()) - Offset::y(font.baseline())
                + Offset::y(2),
            "BOOTLOADER",
            font,
            BLD_FG,
            BLD_BG,
        );

        display::icon_rust_top_right(Point::new(WIDTH, 0), ICON_WARN_TITLE, BLD_FG, BLD_BG);

        display::text_center(
            self.area.top_center() + Offset::y(font.text_height()) - Offset::y(font.baseline())
                + Offset::y(11),
            self.version,
            font,
            BLD_FG,
            BLD_BG,
        );

        display::icon_rust_top_left(Point::new(-1, 0), ICON_WARN_TITLE, BLD_FG, BLD_BG);
    }

    fn bounds(&self, _sink: &mut dyn FnMut(Rect)) {}
}
