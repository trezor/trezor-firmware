use crate::{
    strutil::TString,
    ui::{
        component::{Component, Event, EventCtx, Pad},
        display::{Color, Font, Icon},
        geometry::{Alignment, Insets, Offset, Point, Rect},
        shape::{self, Renderer},
    },
};

use super::super::{
    component::{Button, ButtonMsg},
    constant::WIDTH,
    theme::bootloader::{
        button_bld, button_bld_menu, button_initial, BLD_BG, BUTTON_AREA_START, BUTTON_HEIGHT,
        CONTENT_PADDING, CORNER_BUTTON_AREA, MENU32, WELCOME_COLOR,
    },
};

#[repr(u32)]
#[derive(Copy, Clone, ToPrimitive)]
pub enum ConnectMsg {
    Cancel = 1,
    PairingMode = 2,
    Menu = 3,
}

pub struct Connect {
    fg: Color,
    bg: Pad,
    message: TString<'static>,
    font: Font,
    button: Button,
    menu: Option<Button>,
}

impl Connect {
    pub fn new<T>(message: T, font: Font, fg: Color, initial_setup: bool, show_menu: bool) -> Self
    where
        T: Into<TString<'static>>,
    {
        let (bg, menu_btn, cancel) = if initial_setup {
            (
                WELCOME_COLOR,
                Button::with_icon(Icon::new(MENU32))
                    .styled(button_initial())
                    .with_expanded_touch_area(Insets::uniform(13)),
                Button::with_text("Cancel".into()).styled(button_initial()),
            )
        } else {
            (
                BLD_BG,
                Button::with_icon(Icon::new(MENU32))
                    .styled(button_bld_menu())
                    .with_expanded_touch_area(Insets::uniform(13)),
                Button::with_text("Cancel".into()).styled(button_bld()),
            )
        };

        let menu = if show_menu { Some(menu_btn) } else { None };

        let mut instance = Self {
            fg,
            bg: Pad::with_background(bg),
            message: message.into(),
            font,
            button: cancel,
            menu,
        };

        instance.bg.clear();
        instance
    }
}

impl Component for Connect {
    type Msg = ConnectMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(bounds);
        self.menu.place(CORNER_BUTTON_AREA);
        self.button.place(Rect::new(
            Point::new(CONTENT_PADDING, BUTTON_AREA_START),
            Point::new(WIDTH - CONTENT_PADDING, BUTTON_AREA_START + BUTTON_HEIGHT),
        ));

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(ButtonMsg::Clicked) = self.button.event(ctx, event) {
            return Some(ConnectMsg::Cancel);
        }

        #[cfg(all(feature = "ble", feature = "button"))]
        if let Event::Button(_) = event {
            return Some(ConnectMsg::PairingMode);
        }

        #[cfg(feature = "power_manager")]
        if let Some(ButtonMsg::Clicked) = self.menu.event(ctx, event) {
            return Some(ConnectMsg::Menu);
        };

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.bg.render(target);
        self.button.render(target);
        #[cfg(feature = "power_manager")]
        self.menu.render(target);

        self.message.map(|t| {
            shape::Text::new(
                self.bg.area.center() + Offset::y(self.font.text_height() / 2),
                t,
                self.font,
            )
            .with_fg(self.fg)
            .with_align(Alignment::Center)
            .render(target);
        });
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Connect {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Connect");
        t.string("message", self.message);
    }
}
