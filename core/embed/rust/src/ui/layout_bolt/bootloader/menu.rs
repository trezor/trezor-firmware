use crate::ui::{
    component::{Component, Event, EventCtx, Label, Pad},
    constant::{screen, WIDTH},
    display::Icon,
    geometry::{Insets, Point, Rect},
    shape::Renderer,
};

use super::super::{
    component::{Button, ButtonMsg::Clicked, IconText},
    theme::bootloader::{
        button_bld, button_bld_menu, text_title, BLD_BG, BUTTON_HEIGHT, CONTENT_PADDING,
        CORNER_BUTTON_AREA, CORNER_BUTTON_TOUCH_EXPANSION, FIRE24, REFRESH24, TITLE_AREA, X32,
    },
};

const BUTTON_AREA_START: i16 = 56;
const BUTTON_SPACING: i16 = 8;

#[repr(u32)]
#[derive(Copy, Clone, ToPrimitive)]
pub enum MenuMsg {
    Close = 0xAABBCCDD,
    Reboot = 0x11223344,
    FactoryReset = 0x55667788,
    Bluetooth = 0x99AABBCC,
    PowerOff = 0x751A5BEF,
}

pub struct Menu {
    bg: Pad,
    title: Label<'static>,
    close: Button,
    reboot: Button,
    reset: Button,
    bluetooth: Button,
    poweroff: Button,
}

impl Menu {
    pub fn new() -> Self {
        let content_reboot = IconText::new("REBOOT TREZOR", Icon::new(REFRESH24));
        let content_reset = IconText::new("FACTORY RESET", Icon::new(FIRE24));
        let content_bluetooth = IconText::new("BLUETOOTH", Icon::new(FIRE24));
        let content_poweroff = IconText::new("POWER OFF", Icon::new(FIRE24));

        let mut instance = Self {
            bg: Pad::with_background(BLD_BG),
            title: Label::left_aligned("BOOTLOADER".into(), text_title(BLD_BG))
                .vertically_centered(),

            close: Button::with_icon(Icon::new(X32))
                .styled(button_bld_menu())
                .with_expanded_touch_area(Insets::uniform(CORNER_BUTTON_TOUCH_EXPANSION)),

            reboot: Button::with_icon_and_text(content_reboot).styled(button_bld()),

            reset: Button::with_icon_and_text(content_reset).styled(button_bld()),
            bluetooth: Button::with_icon_and_text(content_bluetooth).styled(button_bld()),
            poweroff: Button::with_icon_and_text(content_poweroff).styled(button_bld()),
        };
        instance.bg.clear();
        instance
    }

    pub fn get_button_pos(&self, i: u8) -> Rect {
        Rect::new(
            Point::new(
                CONTENT_PADDING,
                BUTTON_AREA_START + i as i16 * (BUTTON_HEIGHT + BUTTON_SPACING),
            ),
            Point::new(
                WIDTH - CONTENT_PADDING,
                BUTTON_AREA_START + (i + 1) as i16 * BUTTON_HEIGHT + i as i16 * BUTTON_SPACING,
            ),
        )
    }
}

impl Component for Menu {
    type Msg = MenuMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(screen());
        self.title.place(TITLE_AREA);
        self.close.place(CORNER_BUTTON_AREA);
        self.reboot.place(self.get_button_pos(0));
        self.reset.place(self.get_button_pos(1));
        #[cfg(feature = "ble")]
        self.bluetooth.place(self.get_button_pos(2));
        #[cfg(feature = "power_manager")]
        self.poweroff.place(self.get_button_pos(3));
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
        #[cfg(feature = "ble")]
        if let Some(Clicked) = self.bluetooth.event(ctx, event) {
            return Some(Self::Msg::Bluetooth);
        }
        #[cfg(feature = "power_manager")]
        if let Some(Clicked) = self.poweroff.event(ctx, event) {
            return Some(Self::Msg::PowerOff);
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.bg.render(target);
        self.title.render(target);
        self.close.render(target);
        self.reboot.render(target);
        self.reset.render(target);
        #[cfg(feature = "ble")]
        self.bluetooth.render(target);
        #[cfg(feature = "power_manager")]
        self.poweroff.render(target);
    }
}
