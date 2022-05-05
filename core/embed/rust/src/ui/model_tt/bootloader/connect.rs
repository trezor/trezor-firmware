use crate::ui::component::Pad;
use crate::ui::geometry::Point;
use crate::ui::model_tt::bootloader::theme::{BLD_BG, BLD_TITLE_COLOR};
use crate::ui::model_tt::bootloader::ReturnToC;
use crate::ui::model_tt::theme::FONT_BOLD;
use crate::ui::{
    component::{Component, Event, EventCtx},
    display,
    geometry::Rect,
};

use crate::ui::model_tt::constant::{HEIGHT, WIDTH};

#[repr(u32)]
#[derive(Copy, Clone)]
pub enum ConnectMsg {
    None,
}
impl ReturnToC for ConnectMsg {
    fn return_to_c(&self) -> u32 {
        *self as u32
    }
}

pub struct Connect {
    bg: Pad,
    message: &'static str,
}

impl Connect {
    pub fn new(message: &'static str) -> Self {
        let mut instance = Self {
            bg: Pad::with_background(BLD_BG),
            message,
        };

        instance.bg.clear();
        instance
    }
}

impl Component for Connect {
    type Msg = ConnectMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg
            .place(Rect::new(Point::new(0, 0), Point::new(WIDTH, HEIGHT)));
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        self.bg.paint();
        display::text_top_left(
            Point::new(15, 24),
            self.message,
            FONT_BOLD,
            BLD_TITLE_COLOR,
            BLD_BG,
        );
    }

    fn bounds(&self, _sink: &mut dyn FnMut(Rect)) {}
}
