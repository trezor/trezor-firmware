use crate::ui::{
    component::{Child, Component, Event, EventCtx, Pad},
    display,
    geometry::{Point, Rect},
    model_tt::{
        bootloader::{
            theme::{button_bld_menu_item, BLD_BG, BLD_FG, BLD_TITLE_COLOR},
            ReturnToC,
        },
        component::{Button, ButtonMsg::Clicked},
        theme::{FONT_BOLD, FONT_MEDIUM},
    },
};

use crate::ui::model_tt::constant::{HEIGHT, WIDTH};

#[repr(u32)]
#[derive(Copy, Clone)]
pub enum FwInfoMsg {
    Exit,
}
impl ReturnToC for FwInfoMsg {
    fn return_to_c(&self) -> u32 {
        *self as u32
    }
}

pub struct FwInfo {
    bg: Pad,
    message: &'static str,
    fingerprint: &'static str,
    exit: Child<Button<&'static str>>,
}

impl FwInfo {
    pub fn new(fingerprint: &'static str) -> Self {
        let mut instance = Self {
            bg: Pad::with_background(BLD_BG),
            message: "FIRMWARE FINGERPRINT",
            fingerprint,
            exit: Child::new(Button::with_text("Return to menu").styled(button_bld_menu_item())),
        };

        instance.bg.clear();
        instance
    }
}

impl Component for FwInfo {
    type Msg = FwInfoMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg
            .place(Rect::new(Point::new(0, 0), Point::new(WIDTH, HEIGHT)));
        self.exit.place(Rect::new(
            Point::new(16, 178),
            Point::new(16 + 209, 178 + 48),
        ));

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(Clicked) = self.exit.event(ctx, event) {
            return Some(Self::Msg::Exit);
        };
        None
    }

    fn paint(&mut self) {
        self.bg.paint();
        self.exit.paint();
        let (p0, rest) = self.fingerprint.split_at(16);
        let (p1, rest) = rest.split_at(16);
        let (p2, p3) = rest.split_at(16);
        display::rect_fill(
            Rect::new(Point::new(16, 44), Point::new(WIDTH - 12, 45)),
            BLD_FG,
        );
        display::text_top_left(
            Point::new(15, 24),
            self.message,
            FONT_BOLD,
            BLD_TITLE_COLOR,
            BLD_BG,
        );
        display::text_top_left(Point::new(15, 60), p0, FONT_MEDIUM, BLD_FG, BLD_BG);
        display::text_top_left(Point::new(15, 80), p1, FONT_MEDIUM, BLD_FG, BLD_BG);
        display::text_top_left(Point::new(15, 100), p2, FONT_MEDIUM, BLD_FG, BLD_BG);
        display::text_top_left(Point::new(15, 120), p3, FONT_MEDIUM, BLD_FG, BLD_BG);
    }

    fn bounds(&self, _sink: &mut dyn FnMut(Rect)) {}
}
