use crate::ui::{
    component::{
        text::paragraphs::{ParagraphVecShort, Paragraphs},
        Child, Component, Event, EventCtx, Label, Pad,
    },
    constant::screen,
    display::Icon,
    geometry::{Alignment, Insets, Point, Rect},
    model_tt::{
        bootloader::theme::{button_bld, button_bld_menu, BLD_BG, MENU32},
        component::ButtonMsg::Clicked,
    },
};
use heapless::String;

use crate::ui::model_tt::{
    bootloader::theme::{
        BUTTON_AREA_START, BUTTON_HEIGHT, CONTENT_PADDING, CORNER_BUTTON_AREA, TEXT_TITLE,
        TITLE_AREA, TITLE_Y_ADJUSTMENT,
    },
    component::Button,
    constant::WIDTH,
};

#[repr(u32)]
#[derive(Copy, Clone, ToPrimitive)]
pub enum IntroMsg {
    Menu = 1,
    Host = 2,
}

pub struct Intro<'a> {
    bg: Pad,
    title: Child<Label<String<32>>>,
    menu: Child<Button<&'static str>>,
    host: Child<Button<&'static str>>,
    text: Child<Paragraphs<ParagraphVecShort<&'a str>>>,
}

impl<'a> Intro<'a> {
    pub fn new(bld_version: &'static str, content: Paragraphs<ParagraphVecShort<&'a str>>) -> Self {
        let mut title: String<32> = String::new();
        unwrap!(title.push_str("BOOTLOADER "));
        unwrap!(title.push_str(bld_version));

        Self {
            bg: Pad::with_background(BLD_BG).with_clear(),
            title: Child::new(Label::new(title, Alignment::Start, TEXT_TITLE)),
            menu: Child::new(
                Button::with_icon(Icon::new(MENU32))
                    .styled(button_bld_menu())
                    .with_expanded_touch_area(Insets::uniform(13)),
            ),
            host: Child::new(Button::with_text("INSTALL FIRMWARE").styled(button_bld())),
            text: Child::new(content),
        }
    }
}

impl<'a> Component for Intro<'a> {
    type Msg = IntroMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(screen());

        self.title.place(TITLE_AREA);
        let title_height = self.title.inner().area().height();
        self.title.place(Rect::new(
            Point::new(
                CONTENT_PADDING,
                TITLE_AREA.center().y - (title_height / 2) - TITLE_Y_ADJUSTMENT,
            ),
            Point::new(WIDTH - CONTENT_PADDING, BUTTON_AREA_START - CONTENT_PADDING),
        ));

        self.menu.place(CORNER_BUTTON_AREA);
        self.host.place(Rect::new(
            Point::new(CONTENT_PADDING, BUTTON_AREA_START),
            Point::new(WIDTH - CONTENT_PADDING, BUTTON_AREA_START + BUTTON_HEIGHT),
        ));
        self.text.place(Rect::new(
            Point::new(CONTENT_PADDING, TITLE_AREA.y1 + CONTENT_PADDING),
            Point::new(WIDTH - CONTENT_PADDING, BUTTON_AREA_START - CONTENT_PADDING),
        ));
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

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.menu.bounds(sink);
    }
}
