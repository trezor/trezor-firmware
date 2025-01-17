use crate::{
    strutil::TString,
    ui::{
        component::{Child, Component, Event, EventCtx, Label, Pad},
        constant::screen,
        display::Icon,
        geometry::{Alignment, Insets, Point, Rect},
        shape::Renderer,
    },
};

use super::super::{
    component::{Button, ButtonMsg::Clicked},
    constant::WIDTH,
    theme::bootloader::{
        button_bld, button_bld_menu, text_title, BLD_BG, BUTTON_AREA_START, BUTTON_HEIGHT,
        CONTENT_PADDING, CORNER_BUTTON_AREA, MENU32, TEXT_NORMAL, TEXT_WARNING, TITLE_AREA,
    },
};

#[repr(u32)]
#[derive(Copy, Clone, ToPrimitive)]
pub enum IntroMsg {
    Menu = 1,
    Host = 2,
}

pub struct Intro<'a> {
    bg: Pad,
    title: Child<Label<'a>>,
    menu: Child<Button>,
    host: Child<Button>,
    text: Child<Label<'a>>,
    warn: Option<Child<Label<'a>>>,
}

impl<'a> Intro<'a> {
    pub fn new(title: TString<'a>, content: TString<'a>, fw_ok: bool) -> Self {
        Self {
            bg: Pad::with_background(BLD_BG).with_clear(),
            title: Child::new(Label::left_aligned(title, text_title(BLD_BG)).vertically_centered()),
            menu: Child::new(
                Button::with_icon(Icon::new(MENU32))
                    .styled(button_bld_menu())
                    .with_expanded_touch_area(Insets::uniform(13)),
            ),
            host: Child::new(Button::with_text("INSTALL FIRMWARE".into()).styled(button_bld())),
            text: Child::new(Label::left_aligned(content, TEXT_NORMAL).vertically_centered()),
            warn: (!fw_ok).then_some(Child::new(
                Label::new("FIRMWARE CORRUPTED".into(), Alignment::Start, TEXT_WARNING)
                    .vertically_centered(),
            )),
        }
    }
}

impl<'a> Component for Intro<'a> {
    type Msg = IntroMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(screen());

        self.title.place(TITLE_AREA);
        self.menu.place(CORNER_BUTTON_AREA);
        self.host.place(Rect::new(
            Point::new(CONTENT_PADDING, BUTTON_AREA_START),
            Point::new(WIDTH - CONTENT_PADDING, BUTTON_AREA_START + BUTTON_HEIGHT),
        ));
        if self.warn.is_some() {
            self.warn.place(Rect::new(
                Point::new(CONTENT_PADDING, TITLE_AREA.y1 + CONTENT_PADDING),
                Point::new(
                    WIDTH - CONTENT_PADDING,
                    TITLE_AREA.y1 + CONTENT_PADDING + 30,
                ),
            ));
            self.text.place(Rect::new(
                Point::new(CONTENT_PADDING, TITLE_AREA.y1 + CONTENT_PADDING + 30),
                Point::new(WIDTH - CONTENT_PADDING, BUTTON_AREA_START - CONTENT_PADDING),
            ));
        } else {
            self.text.place(Rect::new(
                Point::new(CONTENT_PADDING, TITLE_AREA.y1 + CONTENT_PADDING),
                Point::new(WIDTH - CONTENT_PADDING, BUTTON_AREA_START - CONTENT_PADDING),
            ));
        }

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

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.bg.render(target);
        self.title.render(target);
        self.text.render(target);
        self.warn.render(target);
        self.host.render(target);
        self.menu.render(target);
    }
}
