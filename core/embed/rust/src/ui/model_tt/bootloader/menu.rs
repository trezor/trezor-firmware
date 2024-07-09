use crate::{
    trezorhal::secbool::{secbool, sectrue},
    ui::{
        component::{Child, Component, Event, EventCtx, Label, Pad},
        constant::{screen, WIDTH},
        display::Icon,
        geometry::{Insets, Point, Rect},
        model_tt::{
            component::{Button, ButtonMsg::Clicked, IconText},
            theme::bootloader::{
                button_bld, button_bld_menu, text_title, BLD_BG, BUTTON_HEIGHT, CONTENT_PADDING,
                CORNER_BUTTON_AREA, CORNER_BUTTON_TOUCH_EXPANSION, FIRE24, REFRESH24, TITLE_AREA,
                X32,
            },
        },
        shape::Renderer,
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
}

pub struct Menu {
    bg: Pad,
    title: Child<Label<'static>>,
    close: Child<Button>,
    reboot: Child<Button>,
    reset: Child<Button>,
}

impl Menu {
    pub fn new(firmware_present: secbool) -> Self {
        let content_reboot = IconText::new("REBOOT TREZOR", Icon::new(REFRESH24));
        let content_reset = IconText::new("FACTORY RESET", Icon::new(FIRE24));

        let mut instance = Self {
            bg: Pad::with_background(BLD_BG),
            title: Child::new(
                Label::left_aligned("BOOTLOADER".into(), text_title(BLD_BG)).vertically_centered(),
            ),
            close: Child::new(
                Button::with_icon(Icon::new(X32))
                    .styled(button_bld_menu())
                    .with_expanded_touch_area(Insets::uniform(CORNER_BUTTON_TOUCH_EXPANSION)),
            ),
            reboot: Child::new(
                Button::with_icon_and_text(content_reboot)
                    .styled(button_bld())
                    .initially_enabled(sectrue == firmware_present),
            ),
            reset: Child::new(Button::with_icon_and_text(content_reset).styled(button_bld())),
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

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.bg.render(target);
        self.title.render(target);
        self.close.render(target);
        self.reboot.render(target);
        self.reset.render(target);
    }
}
