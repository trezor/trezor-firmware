use crate::ui::{
    component::{Child, Component, Event, EventCtx, Label, Pad},
    geometry::{Alignment, Alignment2D, Rect},
};

use super::{
    super::{
        component::{ButtonController, ButtonControllerMsg::Triggered, ButtonLayout, ButtonPos},
        theme::{
            bootloader::{BLD_BG, BLD_FG, TEXT_NORMAL},
            BUTTON_HEIGHT, ICON_WARN_TITLE, TITLE_AREA_HEIGHT,
        },
    },
    ReturnToC,
};

const LEFT_BUTTON_TEXT: &str = "INSTALL FW";
const RIGHT_BUTTON_TEXT: &str = "MENU";

#[repr(u32)]
#[derive(Copy, Clone)]
pub enum IntroMsg {
    GoToMenu = 1,
    InstallFirmware = 2,
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
    warn: Option<Child<Label<&'a str>>>,
}

impl<'a> Intro<'a> {
    pub fn new(title: &'a str, content: &'a str, fw_ok: bool) -> Self {
        Self {
            bg: Pad::with_background(BLD_BG).with_clear(),
            title: Child::new(Label::centered(title, TEXT_NORMAL).vertically_centered()),
            buttons: Child::new(ButtonController::new(ButtonLayout::text_none_text(
                LEFT_BUTTON_TEXT,
                RIGHT_BUTTON_TEXT,
            ))),
            text: Child::new(Label::left_aligned(content, TEXT_NORMAL).vertically_centered()),
            warn: (!fw_ok).then_some(Child::new(
                Label::new("FIRMWARE CORRUPTED", Alignment::Start, TEXT_NORMAL)
                    .vertically_centered(),
            )),
        }
    }
}

impl<'a> Component for Intro<'a> {
    type Msg = IntroMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(bounds);

        // Title on top, buttons on bottom, text in between
        let (title_area, text_and_buttons_area) = bounds.split_top(TITLE_AREA_HEIGHT);
        let (text_area, buttons_area) = text_and_buttons_area.split_bottom(BUTTON_HEIGHT);

        self.title.place(title_area);
        self.buttons.place(buttons_area);
        self.text.place(text_area);

        if self.warn.is_some() {
            let (warn_area, text_area) = text_area.split_top(10);
            self.warn.place(warn_area);
            self.text.place(text_area);
        } else {
            self.text.place(text_area);
        }

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let msg = self.buttons.event(ctx, event);

        if let Some(Triggered(ButtonPos::Left, _)) = msg {
            return Some(Self::Msg::InstallFirmware);
        };
        if let Some(Triggered(ButtonPos::Right, _)) = msg {
            return Some(Self::Msg::GoToMenu);
        };
        None
    }

    fn paint(&mut self) {
        self.bg.paint();
        self.title.paint();
        let area = self.bg.area;
        ICON_WARN_TITLE.draw(area.top_left(), Alignment2D::TOP_LEFT, BLD_FG, BLD_BG);
        ICON_WARN_TITLE.draw(area.top_right(), Alignment2D::TOP_RIGHT, BLD_FG, BLD_BG);
        self.warn.paint();
        self.text.paint();
        self.buttons.paint();
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.title.bounds(sink);
        self.warn.bounds(sink);
        self.text.bounds(sink);
        self.buttons.bounds(sink);
    }
}
