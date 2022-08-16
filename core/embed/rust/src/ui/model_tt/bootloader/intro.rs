use crate::ui::{
    component::{text::paragraphs::Paragraphs, Child, Component, Event, EventCtx, Pad},
    geometry::{LinearPlacement, Point, Rect},
    model_tt::{
        bootloader::{
            theme::{button_bld_menu, button_bld_menu_item, TTBootloaderText, BLD_BG, MENU},
            title::Title,
            ReturnToC,
        },
        component::ButtonMsg::Clicked,
        theme::FONT_MEDIUM,
    },
};

use crate::ui::model_tt::{
    component::Button,
    constant::{HEIGHT, WIDTH},
};

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
    title: Child<Title>,
    menu: Child<Button<&'static str>>,
    host: Child<Button<&'static str>>,
    text: Child<Paragraphs<&'static str>>,
}

impl Intro {
    pub fn new(bld_version: &'static str, vendor: &'static str, version: &'static str) -> Self {
        let p1 = Paragraphs::new()
            .add::<TTBootloaderText>(FONT_MEDIUM, version)
            .add::<TTBootloaderText>(FONT_MEDIUM, vendor)
            .with_placement(LinearPlacement::vertical().align_at_start());

        let mut instance = Self {
            bg: Pad::with_background(BLD_BG),
            title: Child::new(Title::new(bld_version)),
            menu: Child::new(Button::with_icon(MENU).styled(button_bld_menu())),
            host: Child::new(Button::with_text("Connect to host").styled(button_bld_menu_item())),
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
            .place(Rect::new(Point::new(15, 24), Point::new(180, 40)));
        self.menu.place(Rect::new(
            Point::new(187, 15),
            Point::new(187 + 38, 15 + 38),
        ));
        self.host.place(Rect::new(
            Point::new(16, 178),
            Point::new(16 + 209, 178 + 48),
        ));
        self.text
            .place(Rect::new(Point::new(15, 75), Point::new(225, 200)));
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
        self.menu.bounds(sink);
    }
}
