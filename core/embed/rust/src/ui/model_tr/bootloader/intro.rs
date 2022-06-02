use crate::ui::component::Pad;
use crate::ui::geometry::Point;
// use crate::ui::model_tr::bootloader::theme::{
//     button_bld_menu, button_bld_menu_item, TTBootloaderText, BLD_BG, MENU,
// };
use crate::ui::model_tr::bootloader::ReturnToC;
// use crate::ui::model_tr::component::ButtonMsg::Clicked;
// use crate::ui::model_tr::theme::FONT_MEDIUM;
use crate::ui::{
    component::{Child, Component, Event, EventCtx},
    geometry::Rect,
};

use crate::ui::model_tr::component::{ButtonPos, HoldToConfirm, HoldToConfirmMsg};

// use crate::ui::model_tr::component::Button;
use crate::ui::model_tr::constant::{HEIGHT, WIDTH};
use crate::ui::model_tr::theme::BG;

#[repr(u32)]
#[derive(Copy, Clone)]
pub enum IntroMsg {
    Menu = 1,
    Host = 2,
}
impl ReturnToC for IntroMsg {
    fn return_to_c(&self) -> u32 {
        *self as u32
    }
}

pub struct Intro {
    bg: Pad,
    confirm: Child<HoldToConfirm>,
    result: Option<HoldToConfirmMsg>,
}

impl Intro {
    pub fn new() -> Self {
        let mut instance = Self {
            bg: Pad::with_background(BG),
            confirm: Child::new(HoldToConfirm::new(ButtonPos::Right, "HOLD TO CONFIRM")),
            result: None,
        };

        instance.bg.clear();
        instance
    }
}

impl Component for Intro {
    type Msg = IntroMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg
            .place(Rect::new(Point::new(0, 0), Point::new(WIDTH, HEIGHT)));
        // self.confirm
        //     .place(Rect::new(Point::new(-50, -5), Point::new(55, 7)));
        // self.confirm
        //     .place(Rect::new(Point::new(70, 120), Point::new(175, 132)));
        // self.confirm
        //     .place(Rect::new(Point::new(0, 0), Point::new(128, 128)));
        self.confirm
            .place(Rect::new(Point::new(30, 112), Point::new(128, 128)));
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let msg = self.confirm.event(ctx, event);
        if let Some(HoldToConfirmMsg::Confirmed) = msg {
            Some(IntroMsg::Host);
            self.result = Some(HoldToConfirmMsg::Confirmed);
            ctx.request_paint()
        };
        if let Some(HoldToConfirmMsg::FailedToConfirm) = msg {
            Some(IntroMsg::Menu);
            self.result = Some(HoldToConfirmMsg::FailedToConfirm);
            ctx.request_paint()
        };

        None
    }

    fn paint(&mut self) {
        self.bg.paint();
        self.confirm.paint();
    }

    fn bounds(&self, _sink: &mut dyn FnMut(Rect)) {}
}
