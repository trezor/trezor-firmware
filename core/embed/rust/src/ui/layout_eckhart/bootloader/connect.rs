use crate::{
    strutil::TString,
    ui::{
        component::{Component, Event, EventCtx, Label},
        geometry::{Alignment, Rect},
        shape::Renderer,
    },
};

use super::{
    super::{constant::SCREEN, cshape::ScreenBorder, theme},
    BldActionBar, BldActionBarMsg, BldHeader,
};

#[cfg(feature = "power_manager")]
use super::BldHeaderMsg;

#[repr(u32)]
#[derive(Copy, Clone, ToPrimitive)]
pub enum ConnectMsg {
    Cancel = 1,
    PairingMode = 2,
    Menu = 3,
}

pub struct ConnectScreen {
    header: Option<BldHeader<'static>>,
    message: Label<'static>,
    action_bar: Option<BldActionBar>,
    screen_border: ScreenBorder,
}

impl ConnectScreen {
    pub fn new(message: TString<'static>) -> Self {
        Self {
            header: None,
            message: Label::new(message, Alignment::Center, theme::TEXT_NORMAL),
            action_bar: None,
            screen_border: ScreenBorder::new(theme::BLUE),
        }
    }

    pub fn with_header(mut self, header: BldHeader<'static>) -> Self {
        self.header = Some(header);
        self
    }

    pub fn with_action_bar(mut self, action_bar: BldActionBar) -> Self {
        self.action_bar = Some(action_bar);
        self
    }
}

impl Component for ConnectScreen {
    type Msg = ConnectMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (header_area, content_area) = SCREEN.split_top(theme::HEADER_HEIGHT);
        let (content_area, action_bar_area) = content_area.split_bottom(theme::ACTION_BAR_HEIGHT);
        let content_area = content_area.inset(theme::SIDE_INSETS);
        self.header.place(header_area);
        self.action_bar.place(action_bar_area);
        self.message.place(content_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(BldActionBarMsg::Confirmed) = self.action_bar.event(ctx, event) {
            // Single mode ActionBar used to CancelPairing - so we map it to Msg::Cancel
            return Some(ConnectMsg::Cancel);
        }

        #[cfg(all(feature = "ble", feature = "button"))]
        if let Event::Button(_) = event {
            return Some(ConnectMsg::PairingMode);
        }

        #[cfg(feature = "power_manager")]
        if let Some(BldHeaderMsg::Menu) = self.header.event(ctx, event) {
            return Some(ConnectMsg::Menu);
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.message.render(target);
        #[cfg(feature = "power_manager")]
        self.header.render(target);
        self.action_bar.render(target);
        self.screen_border.render(u8::MAX, target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for ConnectScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Connect");
        t.string("message", *self.message.text());
    }
}
