use crate::ui::{
    component::{Child, Component, Event, EventCtx, Never, Pad},
    geometry::{Point, Rect},
};

use super::super::{
    bootloader::{theme::BLD_BG, title::Title},
    constant::{HEIGHT, WIDTH},
};

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
    type Msg = Never;

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
