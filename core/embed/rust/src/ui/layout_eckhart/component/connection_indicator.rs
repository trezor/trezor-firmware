use crate::{
    trezorhal::{ble, usb},
    ui::{
        component::{Component, Event, EventCtx, Never},
        event::{BLEEvent, USBEvent},
        geometry::Rect,
        layout_eckhart::cshape::render_connected_indicator,
        shape::Renderer,
    },
};

use super::super::cshape::INDICATOR_OUTER_RADIUS;

pub struct ConnectionIndicator {
    area: Rect,
    connected: bool,
}

impl ConnectionIndicator {
    pub const AREA_SIZE_NEEDED: i16 = INDICATOR_OUTER_RADIUS + 4;
    pub fn new() -> Self {
        Self {
            area: Rect::zero(),
            connected: false,
        }
    }

    pub fn content_width(&self) -> i16 {
        if self.connected {
            Self::AREA_SIZE_NEEDED
        } else {
            0
        }
    }
}

impl Component for ConnectionIndicator {
    type Msg = ();

    fn place(&mut self, bounds: Rect) -> Rect {
        // enforce that the bounds are big enough to fit the indicator + padding
        debug_assert_eq!(bounds.width(), Self::AREA_SIZE_NEEDED);
        debug_assert_eq!(bounds.height(), Self::AREA_SIZE_NEEDED);
        self.area = bounds;
        self.area
    }

    /// Return Some(()) when the connection status changes, None otherwise
    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let old_connected = self.connected;
        match event {
            Event::Attach(_) => {
                // Only poll on attach
                self.connected = usb::usb_configured() || ble::is_connected();
            }
            Event::USB(USBEvent::Configured) => {
                self.connected = true;
            }
            Event::USB(USBEvent::Deconfigured) => {
                // Only update if BLE is also disconnected
                self.connected = ble::is_connected();
            }
            Event::BLE(BLEEvent::Connected) => {
                self.connected = true;
            }
            Event::BLE(BLEEvent::Disconnected) => {
                // Only update if USB is also disconnected
                self.connected = usb::usb_configured();
            }
            _ => {}
        }
        if self.connected != old_connected {
            ctx.request_paint();
            Some(())
        } else {
            None
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if self.connected {
            render_connected_indicator(self.area.center(), target);
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for ConnectionIndicator {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ConnectionIndicator");
        t.bool("connected", self.connected);
    }
}
