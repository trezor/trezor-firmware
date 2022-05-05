use crate::ui::{
    component::{Child, Component, Event, EventCtx, Pad},
    display::{self, Font},
    geometry::{Point, Rect},
    model_tt::{
        bootloader::theme::{button_bld_menu_item, BLD_BG, BLD_FG, BLD_TITLE_COLOR},
        component::{Button, ButtonMsg::Clicked},
    },
};

use crate::ui::model_tt::constant::{HEIGHT, WIDTH};

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
    type Msg = ();

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
            return Some(());
        };
        None
    }

    fn paint(&mut self) {
        self.bg.paint();
        self.exit.paint();
        display::rect_fill(
            Rect::new(Point::new(16, 44), Point::new(WIDTH - 12, 45)),
            BLD_FG,
        );
        display::text_top_left(
            Point::new(15, 24),
            self.message,
            Font::BOLD,
            BLD_TITLE_COLOR,
            BLD_BG,
        );
        for i in 0..4usize {
            let ypos = (60 + i * 20) as i16;
            let idx = i * 16;
            let part = self.fingerprint.get(idx..idx + 16).unwrap_or("");
            display::text_top_left(Point::new(15, ypos), part, Font::MEDIUM, BLD_FG, BLD_BG);
        }
    }

    fn bounds(&self, _sink: &mut dyn FnMut(Rect)) {}
}
