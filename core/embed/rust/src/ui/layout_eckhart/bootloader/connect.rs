use crate::ui::{
    component::{Component, Event, EventCtx, Label},
    geometry::Rect,
    shape::Renderer,
};

use super::{
    super::{component::Button, constant::SCREEN, cshape::ScreenBorder, theme},
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
    action_bar: BldActionBar,
    screen_border: Option<ScreenBorder>,
}

impl ConnectScreen {
    pub fn new(initial_setup: bool) -> Self {
        let mut btn = Button::with_text("Cancel".into());
        if initial_setup {
            btn = btn.with_gradient(theme::Gradient::DefaultGrey);
        };

        Self {
            header: None,
            message: Label::left_aligned(
                "Waiting for connected device...".into(),
                theme::TEXT_NORMAL,
            ),
            action_bar: BldActionBar::new_single(btn),
            screen_border: None,
        }
    }

    pub fn with_header(mut self, header: BldHeader<'static>) -> Self {
        self.header = Some(header);
        self
    }

    pub fn with_screen_border(mut self, screen_border: ScreenBorder) -> Self {
        self.screen_border = Some(screen_border);
        self
    }
}

impl Component for ConnectScreen {
    type Msg = ConnectMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (header_area, content_area) = if self.header.is_some() {
            SCREEN.split_top(theme::HEADER_HEIGHT)
        } else {
            SCREEN.split_top(theme::PROGRESS_TEXT_ORIGIN.y)
        };
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
        if let Some(screen_border) = &self.screen_border {
            screen_border.render(u8::MAX, target);
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for ConnectScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Connect");
        t.string("message", *self.message.text());
    }
}
