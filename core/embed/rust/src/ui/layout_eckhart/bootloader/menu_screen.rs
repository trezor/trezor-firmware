use crate::{
    trezorhal::secbool::{secbool, sectrue},
    ui::{
        component::{Child, Component, Event, EventCtx, Label, Pad},
        constant::{screen, WIDTH},
        geometry::{Insets, Point, Rect},
        shape::Renderer,
    },
};

use super::super::{
    component::{Button, ButtonMsg::Clicked},
    theme::{
        bootloader::{
            button_bld, button_bld_menu, text_title, BLD_BG, BUTTON_HEIGHT, CONTENT_PADDING,
            CORNER_BUTTON_AREA, CORNER_BUTTON_TOUCH_EXPANSION, TITLE_AREA,
        },
        ICON_CLOSE,
    },
};

const BUTTON_AREA_START: i16 = 56;
const BUTTON_SPACING: i16 = 8;

#[repr(u32)]
#[derive(Copy, Clone, ToPrimitive)]
pub enum BldMenuMsg {
    Close = 0xAABBCCDD,
    Reboot = 0x11223344,
    FactoryReset = 0x55667788,
}

pub struct BldMenuScreen {
    bg: Pad,
    title: Child<Label<'static>>,
    close: Child<Button>,
    header: BldHeader<'static>,
    bluetooth: Button,
    reboot: Button,
    reset: Button,
}

impl BldMenuScreen {
    pub fn new(firmware_present: secbool) -> Self {
        let mut instance = Self {
            bg: Pad::with_background(BLD_BG),
            title: Child::new(
                Label::left_aligned("Bootloader".into(), text_title(BLD_BG)).vertically_centered(),
            ),
            close: Child::new(
                Button::with_icon(ICON_CLOSE)
                    .styled(button_bld_menu())
                    .with_expanded_touch_area(Insets::uniform(CORNER_BUTTON_TOUCH_EXPANSION)),
            ),
            reboot: Child::new(
                Button::with_text("Reboot Trezor".into())
                    .styled(button_bld())
                    .initially_enabled(sectrue == firmware_present),
            ),
            reset: Child::new(Button::with_text("Factory reset".into()).styled(button_bld())),
        };
        instance.bg.clear();
        instance
    }
}

impl Component for BldMenuScreen {
    type Msg = BldMenuMsg;

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

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.bg.render(target);
        self.title.render(target);
        self.close.render(target);
        self.reboot.render(target);
        self.reset.render(target);
    }
}
