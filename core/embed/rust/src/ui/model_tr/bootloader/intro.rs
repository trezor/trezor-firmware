use crate::ui::{
    component::{
        text::paragraphs::{Paragraph, ParagraphVecShort, Paragraphs, VecExt},
        Child, Component, Event, EventCtx, Pad,
    },
    geometry::{LinearPlacement, Point, Rect},
    model_tr::{
        bootloader::{
            theme::{BLD_BG, TEXT_NORMAL},
            title::Title,
            ReturnToC,
        },
        component::ButtonMsg::Clicked,
    },
};

use crate::ui::model_tr::{
    bootloader::theme::bld_button_default,
    component::{Button, ButtonPos},
    constant::{HEIGHT, WIDTH},
};

#[repr(u32)]
#[derive(Copy, Clone)]
pub enum IntroMsg {
    Menu = 1,
    Host = 2,
}
impl ReturnToC for IntroMsg {
    fn return_to_c(self) -> u32 {
        self as u32
    }
}

pub struct Intro {
    bg: Pad,
    title: Child<Title>,
    host: Child<Button<&'static str>>,
    menu: Child<Button<&'static str>>,
    text: Child<Paragraphs<ParagraphVecShort<&'static str>>>,
}

impl Intro {
    pub fn new(bld_version: &'static str, vendor: &'static str, version: &'static str) -> Self {
        let mut messages = ParagraphVecShort::new();

        messages.add(Paragraph::new(&TEXT_NORMAL, version));
        messages.add(Paragraph::new(&TEXT_NORMAL, vendor));

        let p1 =
            Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_start());

        let mut instance = Self {
            bg: Pad::with_background(BLD_BG),
            title: Child::new(Title::new(bld_version)),
            host: Child::new(Button::with_text(
                ButtonPos::Left,
                "INSTALL FIRMWARE",
                bld_button_default(),
            )),
            menu: Child::new(Button::with_text(
                ButtonPos::Right,
                "MENU",
                bld_button_default(),
            )),
            text: Child::new(p1),
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
        self.title
            .place(Rect::new(Point::new(10, 0), Point::new(128, 8)));

        let button_area = bounds.split_bottom(12).1;
        self.host.place(button_area);
        self.menu.place(button_area);

        self.text
            .place(Rect::new(Point::new(10, 20), Point::new(118, 50)));
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(Clicked) = self.menu.event(ctx, event) {
            return Some(Self::Msg::Menu);
        };
        if let Some(Clicked) = self.host.event(ctx, event) {
            return Some(Self::Msg::Host);
        };
        None
    }

    fn paint(&mut self) {
        self.bg.paint();
        self.title.paint();
        self.text.paint();
        self.host.paint();
        self.menu.paint();
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.title.bounds(sink);
        self.text.bounds(sink);
        self.host.bounds(sink);
        self.menu.bounds(sink);
    }
}
