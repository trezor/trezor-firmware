use crate::ui::{
    component::{Component, Event, EventCtx},
    geometry::{Alignment, Rect},
    layout_eckhart::component::Button,
    shape::Renderer,
};

use super::{
    super::{
        cshape::ScreenBorder,
        theme::{bootloader::button_bld_menu, BLUE, HEADER_HEIGHT},
    },
    bld_menu::BldMenuSelectionMsg,
    BldHeader, BldHeaderMsg, BldMenu,
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
    header: BldHeader<'static>,
    menu: BldMenu,
    screen_border: ScreenBorder,
}

impl BldMenuScreen {
    pub fn new(firmware_present: bool) -> Self {
        let bluetooth = Button::with_text("Bluetooth".into())
            .styled(button_bld_menu())
            .with_text_align(Alignment::Start)
            .initially_enabled(false);
        let reboot = Button::with_text("Reboot Trezor".into())
            .styled(button_bld_menu())
            .with_text_align(Alignment::Start)
            .initially_enabled(firmware_present);
        let reset = Button::with_text("Factory reset".into())
            .styled(button_bld_menu())
            .with_text_align(Alignment::Start);

        let menu = BldMenu::empty().item(bluetooth).item(reboot).item(reset);
        Self {
            header: BldHeader::new("Bootloader".into()).with_close_button(),
            menu,
            screen_border: ScreenBorder::new(BLUE),
        }
    }
}

impl Component for BldMenuScreen {
    type Msg = BldMenuMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (header_area, menu_area) = bounds.split_top(HEADER_HEIGHT);

        self.header.place(header_area);
        self.menu.place(menu_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(BldHeaderMsg::Cancelled) = self.header.event(ctx, event) {
            return Some(Self::Msg::Close);
        }

        if let Some(BldMenuSelectionMsg::Selected(n)) = self.menu.event(ctx, event) {
            match n {
                0 => return Some(Self::Msg::Close),
                1 => return Some(Self::Msg::Reboot),
                2 => return Some(Self::Msg::FactoryReset),
                _ => {}
            }
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.header.render(target);
        self.menu.render(target);
        self.screen_border.render(u8::MAX, target);
    }
}
