use crate::ui::component::Pad;
use crate::ui::geometry::Point;
use crate::ui::model_tt::bootloader::theme::{BLD_BG, BLD_FG, RECEIVE};
use crate::ui::model_tt::bootloader::ReturnToC;
use crate::ui::model_tt::constant::{HEIGHT, WIDTH};
use crate::ui::model_tt::theme::FONT_MEDIUM;
use crate::ui::{
    component::{Component, Event, EventCtx},
    display,
    geometry::Rect,
};

#[repr(u32)]
#[derive(Copy, Clone)]
pub enum ProgressMsg {
    None,
}
impl ReturnToC for ProgressMsg {
    fn return_to_c(&self) -> u32 {
        *self as u32
    }
}

pub struct Progress {
    bg: Pad,
    text: &'static str,
    icon: &'static [u8],
    progress: u16,
}

impl Progress {
    pub fn new(text: &'static str, clear: bool) -> Self {
        let mut instance = Self {
            bg: Pad::with_background(BLD_BG),
            text,
            icon: RECEIVE,
            progress: 0,
        };
        if clear {
            instance.bg.clear();
        }
        instance
    }

    pub fn set_progress(&mut self, progress: u16) {
        self.progress = progress;
    }
}

impl Component for Progress {
    type Msg = ProgressMsg;

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
        display::text_center(
            Point::new(WIDTH / 2, 214),
            self.text,
            FONT_MEDIUM,
            BLD_FG,
            BLD_BG,
        );
        display::loader(
            self.progress,
            -20,
            BLD_FG,
            BLD_BG,
            Some((self.icon, BLD_FG)),
        );
    }

    fn bounds(&self, _sink: &mut dyn FnMut(Rect)) {}
}
