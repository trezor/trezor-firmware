use crate::{
    trezorhal::secbool::{secbool, sectrue},
    ui::{
        component::{Component, Event, EventCtx, Label, Pad},
        constant::{screen, WIDTH},
        display::Icon,
        geometry::{Insets, Point, Rect},
        shape::Renderer,
    },
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
    TurnOff = 0x99AABBCC,
}

pub struct Menu {
    bg: Pad,
    title: Label<'static>,
    close: Button,
    reboot: Button,
    reset: Button,
    turn_off: Option<Button>,
}

impl Menu {
    pub fn new(firmware_present: secbool) -> Self {
        let content_reboot = IconText::new("REBOOT TREZOR", Icon::new(REFRESH24));
        let content_reset = IconText::new("FACTORY RESET", Icon::new(FIRE24));

        let turn_off = IconText::new("TURN OFF", Icon::new(FIRE24));

        #[cfg(not(feature = "powerctl"))]
        let turn_off_menu_item = false;
        #[cfg(feature = "powerctl")]
        let turn_off_menu_item = true;

        let mut instance = Self {
            bg: Pad::with_background(BLD_BG),
            title: Label::left_aligned("BOOTLOADER".into(), text_title(BLD_BG))
                .vertically_centered(),
            close: Button::with_icon(Icon::new(X32))
                .styled(button_bld_menu())
                .with_expanded_touch_area(Insets::uniform(CORNER_BUTTON_TOUCH_EXPANSION)),
            reboot: Button::with_icon_and_text(content_reboot)
                .styled(button_bld())
                .initially_enabled(sectrue == firmware_present),
            reset: Button::with_icon_and_text(content_reset).styled(button_bld()),
            turn_off: if turn_off_menu_item {
                Some(Button::with_icon_and_text(turn_off).styled(button_bld()))
            } else {
                None
            },
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
            Point::new(CONTENT_PADDING, BUTTON_AREA_START),
            Point::new(WIDTH - CONTENT_PADDING, BUTTON_AREA_START + BUTTON_HEIGHT),
        ));
        self.reset.place(Rect::new(
            Point::new(
                CONTENT_PADDING,
                BUTTON_AREA_START + BUTTON_HEIGHT + BUTTON_SPACING,
            ),
            Point::new(
                WIDTH - CONTENT_PADDING,
                BUTTON_AREA_START + 2 * BUTTON_HEIGHT + BUTTON_SPACING,
            ),
        ));
        self.turn_off.place(Rect::new(
            Point::new(
                CONTENT_PADDING,
                BUTTON_AREA_START + 2 * BUTTON_HEIGHT + 2 * BUTTON_SPACING,
            ),
            Point::new(
                WIDTH - CONTENT_PADDING,
                BUTTON_AREA_START + 3 * BUTTON_HEIGHT + 2 * BUTTON_SPACING,
            ),
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
        if let Some(Clicked) = self.turn_off.event(ctx, event) {
            return Some(Self::Msg::TurnOff);
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.bg.render(target);
        self.title.render(target);
        self.close.render(target);
        self.reboot.render(target);
        self.reset.render(target);
        self.turn_off.render(target);
    }
}
