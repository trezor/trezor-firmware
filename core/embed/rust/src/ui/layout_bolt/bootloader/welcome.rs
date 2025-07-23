use super::super::{
    fonts,
    theme::{
        bootloader::{START_URL, WELCOME_COLOR},
        GREY_MEDIUM, WHITE,
    },
};
use crate::ui::{
    component::{Component, Event, EventCtx, Pad},
    constant::screen,
    display::{toif::Toif, Icon},
    geometry::{Alignment, Alignment2D, Insets, Offset, Rect},
    shape::{self, Renderer},
};

use super::super::{
    component::Button,
    theme::bootloader::{button_initial, CORNER_BUTTON_AREA, MENU32},
};

#[cfg(feature = "power_manager")]
use super::super::component::ButtonMsg::Clicked;

#[repr(u32)]
#[derive(Copy, Clone, ToPrimitive)]
pub enum WelcomeMsg {
    Cancel = 1,
    PairingMode = 2,
    Menu = 3,
}

pub struct Welcome {
    bg: Pad,
    menu: Button,
}

impl Welcome {
    pub fn new() -> Self {
        Self {
            bg: Pad::with_background(WELCOME_COLOR).with_clear(),
            menu: Button::with_icon(Icon::new(MENU32))
                .styled(button_initial())
                .with_expanded_touch_area(Insets::uniform(13)),
        }
    }
}

impl Component for Welcome {
    type Msg = WelcomeMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(screen());
        self.menu.place(CORNER_BUTTON_AREA);
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        #[cfg(all(feature = "ble", feature = "button"))]
        if let Event::Button(_) = _event {
            return Some(WelcomeMsg::PairingMode);
        }
        #[cfg(feature = "power_manager")]
        if let Some(Clicked) = self.menu.event(_ctx, _event) {
            return Some(WelcomeMsg::Menu);
        };
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.bg.render(target);
        #[cfg(feature = "power_manager")]
        self.menu.render(target);

        shape::Text::new(
            screen().top_center() + Offset::y(102),
            "Get started with",
            fonts::FONT_NORMAL,
        )
        .with_align(Alignment::Center)
        .with_fg(GREY_MEDIUM)
        .render(target);

        shape::Text::new(
            screen().top_center() + Offset::y(126),
            "your Trezor at",
            fonts::FONT_NORMAL,
        )
        .with_align(Alignment::Center)
        .with_fg(GREY_MEDIUM)
        .render(target);

        let icon = unwrap!(Toif::new(START_URL));
        shape::ToifImage::new(screen().top_center() + Offset::y(135), icon)
            .with_align(Alignment2D::TOP_CENTER)
            .with_fg(WHITE)
            .render(target);
    }
}
