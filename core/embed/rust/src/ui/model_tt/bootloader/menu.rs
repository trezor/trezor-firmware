use crate::ui::{
    component::{Child, Component, Event, EventCtx, Label, Pad},
    constant::{screen, WIDTH},
    display::Icon,
    geometry::{Alignment, Insets, Point, Rect},
    model_tt::{
        bootloader::theme::{
            button_bld_menu, button_bld_menu_item, BLD_BG, CLOSE, CONTENT_PADDING,
            CORNER_BUTTON_AREA, ERASE, REBOOT, TEXT_TITLE, TITLE_AREA,
        },
        component::{Button, ButtonMsg::Clicked, IconText},
    },
};
use heapless::String;

#[repr(u32)]
#[derive(Copy, Clone, ToPrimitive)]
pub enum MenuMsg {
    Close = 1,
    Reboot = 2,
    FactoryReset = 3,
}

pub struct Menu {
    bg: Pad,
    title: Child<Label<String<32>>>,
    close: Child<Button<&'static str>>,
    reboot: Child<Button<&'static str>>,
    reset: Child<Button<&'static str>>,
}

impl Menu {
    pub fn new(bld_version: &'static str) -> Self {
        let content_reboot = IconText::new("REBOOT TREZOR", Icon::new(REBOOT));
        let content_reset = IconText::new("FACTORY RESET", Icon::new(ERASE));

        let mut title: String<32> = String::new();
        unwrap!(title.push_str("BOOTLOADER "));
        unwrap!(title.push_str(bld_version));

        let mut instance = Self {
            bg: Pad::with_background(BLD_BG),
            title: Child::new(Label::new(title, Alignment::Start, TEXT_TITLE)),
            close: Child::new(
                Button::with_icon(Icon::new(CLOSE))
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
        self.bg.place(screen());
        self.title.place(TITLE_AREA);
        self.close.place(CORNER_BUTTON_AREA);
        self.reboot.place(Rect::new(
            Point::new(CONTENT_PADDING, 64),
            Point::new(WIDTH - CONTENT_PADDING, 64 + 38),
        ));
        self.reset.place(Rect::new(
            Point::new(CONTENT_PADDING, 110),
            Point::new(WIDTH - CONTENT_PADDING, 110 + 38),
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
