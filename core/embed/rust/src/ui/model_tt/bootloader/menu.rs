use crate::ui::{
    component::{Child, Component, Event, EventCtx, Pad},
    geometry::{Insets, Point, Rect},
    model_tt::{
        bootloader::{
            theme::{button_bld_menu, button_bld_menu_item, BLD_BG, CLOSE, ERASE, REBOOT},
            title::Title,
            ReturnToC,
        },
        component::{Button, ButtonMsg::Clicked, IconText},
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
    close: Child<Button<&'static str>>,
    reboot: Child<Button<&'static str>>,
    reset: Child<Button<&'static str>>,
}

impl Menu {
    pub fn new(bld_version: &'static str) -> Self {
        let content_reboot = IconText::new("REBOOT TREZOR", REBOOT);
        let content_reset = IconText::new("WIPE TREZOR", ERASE);

        let mut instance = Self {
            bg: Pad::with_background(BLD_BG),
            title: Child::new(Title::new(bld_version)),
            close: Child::new(
                Button::with_icon(CLOSE)
                    .styled(button_bld_menu())
                    .with_expanded_touch_area(Insets::uniform(13)),
            ),
            reboot: Child::new(
                Button::with_icon_and_text(content_reboot).styled(button_bld_menu_item()),
            ),
            reset: Child::new(
                Button::with_icon_and_text(content_reset).styled(button_bld_menu_item()),
            ),
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
            .place(Rect::new(Point::new(15, 24), Point::new(180, 40)));
        self.close.place(Rect::new(
            Point::new(187, 15),
            Point::new(187 + 38, 15 + 38),
        ));
        self.reboot
            .place(Rect::new(Point::new(16, 66), Point::new(16 + 209, 66 + 48)));
        self.reset.place(Rect::new(
            Point::new(16, 122),
            Point::new(16 + 209, 122 + 48),
        ));
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(Clicked) = self.close.event(ctx, event) {
            return Some(Self::Msg::Close);
        }
        if let Some(Clicked) = self.reboot.event(ctx, event) {
            return Some(Self::Msg::Reboot);
        }
        if let Some(Clicked) = self.reset.event(ctx, event) {
            return Some(Self::Msg::FactoryReset);
        }

        None
    }

    fn paint(&mut self) {
        self.bg.paint();
        self.title.paint();
        self.close.paint();
        self.reboot.paint();
        self.reset.paint();
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.close.bounds(sink);
        self.reboot.bounds(sink);
        self.reset.bounds(sink);
    }
}
