use crate::ui::{
    component::{Child, Component, ComponentExt, Event, EventCtx, Label, Pad},
    constant::screen,
    display::Icon,
    geometry::{Alignment, Point, Rect, TOP_LEFT, TOP_RIGHT},
    model_tr::bootloader::{
        theme::{BLD_BG, TEXT_NORMAL},
        ReturnToC,
    },
};

use crate::ui::model_tr::{
    bootloader::theme::BLD_FG,
    component::{ButtonController, ButtonControllerMsg::Triggered, ButtonLayout, ButtonPos},
    constant::{HEIGHT, WIDTH},
    theme::{BUTTON_HEIGHT, ICON_WARN_TITLE, TITLE_AREA_HEIGHT},
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

pub struct Intro<'a> {
    bg: Pad,
    title: Child<Label<&'a str>>,
    buttons: Child<ButtonController<&'static str>>,
    text: Child<Label<&'a str>>,
}

impl<'a> Intro<'a> {
    pub fn new(title: &'a str, content: &'a str) -> Self {
        let mut instance = Self {
            bg: Pad::with_background(BLD_BG).with_clear(),
            title: Child::new(
                Label::new(title, Alignment::Center, TEXT_NORMAL)
                    .vertically_aligned(Alignment::Start),
            ),
            buttons: ButtonController::new(ButtonLayout::text_none_text("INSTALL FW", "MENU"))
                .into_child(),
            text: Child::new(
                Label::new(content, Alignment::Start, TEXT_NORMAL)
                    .vertically_aligned(Alignment::Center),
            ),
        };

        instance.bg.clear();
        instance
    }
}

impl<'a> Component for Intro<'a> {
    type Msg = IntroMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(screen());

        self.title.place(Rect::new(
            Point::zero(),
            Point::new(WIDTH, TITLE_AREA_HEIGHT),
        ));

        self.buttons.place(bounds.split_bottom(BUTTON_HEIGHT).1);

        self.text.place(Rect::new(
            Point::new(0, TITLE_AREA_HEIGHT),
            Point::new(WIDTH, HEIGHT - BUTTON_HEIGHT),
        ));
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let msg = self.buttons.event(ctx, event);

        if let Some(Triggered(ButtonPos::Left)) = msg {
            return Some(Self::Msg::Host);
        };
        if let Some(Triggered(ButtonPos::Right)) = msg {
            return Some(Self::Msg::Menu);
        };
        None
    }

    fn paint(&mut self) {
        self.bg.paint();
        self.title.paint();

        Icon::new(ICON_WARN_TITLE).draw(screen().top_left(), TOP_LEFT, BLD_FG, BLD_BG);
        Icon::new(ICON_WARN_TITLE).draw(screen().top_right(), TOP_RIGHT, BLD_FG, BLD_BG);
        self.text.paint();
        self.buttons.paint();
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.title.bounds(sink);
        self.text.bounds(sink);
        self.buttons.bounds(sink);
    }
}
