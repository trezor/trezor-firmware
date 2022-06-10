use crate::time::Instant;
use crate::ui::component::{ComponentExt, Pad};
use crate::ui::geometry::{Offset, Point};
// use crate::ui::model_tr::bootloader::theme::{
//     button_bld_menu, button_bld_menu_item, TTBootloaderText, BLD_BG, MENU,
// };
use crate::ui::model_tr::bootloader::ReturnToC;
// use crate::ui::model_tr::component::ButtonMsg::Clicked;
// use crate::ui::model_tr::theme::FONT_MEDIUM;
use crate::ui::model_tr::bootloader::intro::State::{Confirmed, Initial, Returned};
use crate::ui::{
    component::{Child, Component, Event, EventCtx},
    geometry::Rect,
};

use crate::ui::model_tr::component::{
    ButtonPos, HoldToConfirm, HoldToConfirmMsg, ResultAnim, ResultPopup, ResultPopupMessage,
};

// use crate::ui::model_tr::component::Button;
use crate::ui::model_tr::constant::{HEIGHT, WIDTH};
use crate::ui::model_tr::theme::{BG, ICON_FAIL, ICON_SUCCESS};

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

enum State {
    Initial,
    Confirmed,
    Returned,
}

pub struct Intro {
    bg: Pad,
    state: State,
    anim: Child<ResultAnim>,
    confirm: Child<HoldToConfirm>,
    result: Child<ResultPopup>,
}

impl Intro {
    pub fn new() -> Self {
        let mut result_popup = ResultPopup::new(
            ICON_SUCCESS,
            "Something has been a success",
            Some("Headline"),
            Some("GOT IT"),
        );
        result_popup.autoclose();

        let mut instance = Self {
            bg: Pad::with_background(BG),
            state: Initial,
            confirm: Child::new(HoldToConfirm::new(ButtonPos::Right, "HOLD TO CONFIRM")),
            result: Child::new(result_popup),
            anim: Child::new(ResultAnim::new(ICON_FAIL)),
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
        self.result
            .place(Rect::new(Point::new(0, 0), Point::new(WIDTH, HEIGHT)));
        self.anim.place(Rect::from_top_left_and_size(
            Point::new(10, 10),
            Offset::new(18, 18),
        ));
        // self.confirm
        //     .place(Rect::new(Point::new(70, 120), Point::new(175, 132)));
        // self.confirm
        //     .place(Rect::new(Point::new(0, 0), Point::new(128, 128)));
        self.confirm
            .place(Rect::new(Point::new(30, 115), Point::new(128, 128)));
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let State::Confirmed = self.state {
            let msg = self.result.event(ctx, event);
            if let Some(ResultPopupMessage::Confirmed) = msg {
                self.state = Returned;
                self.bg.clear();
                self.anim.request_complete_repaint(ctx);
                self.confirm.request_complete_repaint(ctx);
                ctx.request_paint()
            };
        } else {
            if let State::Initial = self.state {
                //initial
                self.anim.mutate(ctx, |ctx, r| {
                    r.start_growing(ctx, Instant::now());
                });
                self.state = State::Returned;
            }

            let msg = self.confirm.event(ctx, event);
            if let Some(HoldToConfirmMsg::Confirmed) = msg {
                self.state = Confirmed;
                self.bg.clear();
                self.result.mutate(ctx, |ctx, r| {
                    r.reset(ctx);
                });
                self.result.event(ctx, event);
                ctx.request_paint()
            };

            self.anim.event(ctx, event);
        }
        None
    }

    fn paint(&mut self) {
        self.bg.paint();
        if let State::Confirmed = self.state {
            self.result.paint();
        } else {
            self.anim.paint();
            self.confirm.paint();
        }
    }

    fn bounds(&self, _sink: &mut dyn FnMut(Rect)) {}
}
