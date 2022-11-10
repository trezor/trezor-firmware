use crate::ui::{
    component::{
        text::paragraphs::{Paragraph, ParagraphVecShort, Paragraphs, VecExt},
        Child, Component, Event, EventCtx, Pad,
    },
    geometry::{LinearPlacement, Point, Rect},
    model_tr::bootloader::{
        theme::{BLD_BG, TEXT_NORMAL},
        title::Title,
        ReturnToC,
    },
};

use crate::ui::model_tr::{
    component::{ButtonController, ButtonControllerMsg, ButtonLayout, ButtonPos},
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
    buttons: ButtonController,
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
            buttons: ButtonController::new(ButtonLayout::text_none_text(
                "INSTALL FW".into(),
                "MENU".into(),
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
            .place(Rect::new(Point::new(0, 0), Point::new(128, 8)));

        let button_area = bounds.split_bottom(12).1;
        self.buttons.place(button_area);

        self.text
            .place(Rect::new(Point::new(0, 25), Point::new(128, 50)));
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let event = self.buttons.event(ctx, event);
        match event {
            Some(ButtonControllerMsg::Triggered(ButtonPos::Left)) => {
                return Some(Self::Msg::Host);
            }
            Some(ButtonControllerMsg::Triggered(ButtonPos::Right)) => {
                return Some(Self::Msg::Menu);
            }
            _ => {}
        }

        None
    }

    fn paint(&mut self) {
        self.bg.paint();
        self.title.paint();
        self.text.paint();
        self.buttons.paint();
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.title.bounds(sink);
        self.text.bounds(sink);
        self.buttons.bounds(sink);
    }
}
