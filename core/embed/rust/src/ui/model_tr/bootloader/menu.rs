use crate::ui::{
    component::{Child, Component, Event, EventCtx, Pad},
    geometry::{Point, Rect},
    model_tr::{
        bootloader::{theme::BLD_BG, title::Title, ReturnToC},
        constant::{HEIGHT, WIDTH},
    },
};

#[repr(u32)]
#[derive(Copy, Clone)]
pub enum MenuMsg {
    Close = 1,
    Reboot = 2,
    FactoryReset = 3,
}
impl ReturnToC for MenuMsg {
    fn return_to_c(self) -> u32 {
        self as u32
    }
}

pub struct Menu {
    bg: Pad,
    title: Child<Title>,
}

impl Menu {
    pub fn new(bld_version: &'static str) -> Self {
        let mut instance = Self {
            bg: Pad::with_background(BLD_BG),
            title: Child::new(Title::new(bld_version)),
        };
        instance.bg.clear();
        instance
    }
}

impl Component for Menu {
    type Msg = MenuMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg
            .place(Rect::new(Point::new(0, 0), Point::new(WIDTH, HEIGHT)));
        self.title
            .place(Rect::new(Point::new(10, 0), Point::new(128, 8)));
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        self.bg.paint();
        self.title.paint();
    }
}
