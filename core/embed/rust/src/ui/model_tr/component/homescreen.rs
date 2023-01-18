use crate::{
    micropython::buffer::StrBuffer,
    ui::{
        component::{Component, Event, EventCtx, Pad},
        display::Font,
        event::{ButtonEvent, USBEvent},
        geometry::{Offset, Point, Rect},
        model_tr::constant,
    },
};

use super::{common::display_center, theme};

const AREA: Rect = constant::screen();
const TOP_CENTER: Point = AREA.top_center();
const LABEL_Y: i16 = 62;
const LOCKED_Y: i16 = 32;
const TAP_Y: i16 = 47;

pub struct Homescreen {
    label: StrBuffer,
    notification: Option<(StrBuffer, u8)>,
    usb_connected: bool,
    pad: Pad,
}

pub enum HomescreenMsg {
    Dismissed,
}

impl Homescreen {
    pub fn new(label: StrBuffer, notification: Option<(StrBuffer, u8)>) -> Self {
        Self {
            label,
            notification,
            usb_connected: true,
            pad: Pad::with_background(theme::BG),
        }
    }

    fn paint_notification(&self) {
        let baseline = TOP_CENTER + Offset::y(Font::MONO.line_height());
        if !self.usb_connected {
            display_center(baseline, &"NO USB CONNECTION", Font::MONO);
        } else if let Some((notification, _level)) = &self.notification {
            display_center(baseline, &notification.as_ref(), Font::MONO);
        }
    }

    fn event_usb(&mut self, ctx: &mut EventCtx, event: Event) {
        if let Event::USB(USBEvent::Connected(is_connected)) = event {
            if self.usb_connected != is_connected {
                self.usb_connected = is_connected;
                ctx.request_paint();
            }
        }
    }
}

impl Component for Homescreen {
    type Msg = HomescreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.pad.place(AREA);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        Self::event_usb(self, ctx, event);
        None
    }

    fn paint(&mut self) {
        self.pad.paint();
        self.paint_notification();
        display_center(
            TOP_CENTER + Offset::y(LABEL_Y),
            &self.label.as_ref(),
            Font::BOLD,
        );
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.pad.area);
    }
}

pub struct Lockscreen {
    label: StrBuffer,
    bootscreen: bool,
}

impl Lockscreen {
    pub fn new(label: StrBuffer, bootscreen: bool) -> Self {
        Lockscreen { label, bootscreen }
    }
}

impl Component for Lockscreen {
    type Msg = HomescreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Event::Button(ButtonEvent::ButtonReleased(_)) = event {
            return Some(HomescreenMsg::Dismissed);
        }
        None
    }

    fn paint(&mut self) {
        let (locked, tap) = if self.bootscreen {
            ("NOT CONNECTED", "Click to connect")
        } else {
            ("LOCKED", "Click to unlock")
        };
        display_center(TOP_CENTER + Offset::y(LOCKED_Y), &locked, Font::MONO);
        display_center(TOP_CENTER + Offset::y(TAP_Y), &tap, Font::MONO);
        display_center(
            TOP_CENTER + Offset::y(LABEL_Y),
            &self.label.as_ref(),
            Font::BOLD,
        );
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Homescreen {
    fn trace(&self, d: &mut dyn crate::trace::Tracer) {
        d.open("Homescreen");
        d.field("label", &self.label.as_ref());
        d.close();
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Lockscreen {
    fn trace(&self, d: &mut dyn crate::trace::Tracer) {
        d.open("Lockscreen");
        d.field("label", &self.label.as_ref());
        d.close();
    }
}
