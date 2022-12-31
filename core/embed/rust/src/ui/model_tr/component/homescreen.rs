use crate::ui::{
    component::{Component, Event, EventCtx, Pad},
    display::Font,
    event::{ButtonEvent, USBEvent},
    geometry::{Offset, Point, Rect},
    model_tr::constant,
};

use super::{common::display_center, theme};

const AREA: Rect = constant::screen();
const TOP_CENTER: Point = AREA.top_center();
const LABEL_Y: i16 = 62;
const LOCKED_Y: i16 = 32;
const TAP_Y: i16 = 47;

pub struct Homescreen<T> {
    label: T,
    notification: Option<(T, u8)>,
    usb_connected: bool,
    pad: Pad,
}

pub enum HomescreenMsg {
    Dismissed,
}

impl<T> Homescreen<T>
where
    T: AsRef<str>,
{
    pub fn new(label: T, notification: Option<(T, u8)>) -> Self {
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

impl<T> Component for Homescreen<T>
where
    T: AsRef<str>,
{
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

#[cfg(feature = "ui_debug")]
impl<T: AsRef<str>> crate::trace::Trace for Homescreen<T> {
    fn trace(&self, d: &mut dyn crate::trace::Tracer) {
        d.open("Homescreen");
        d.kw_pair("active_page", "0");
        d.kw_pair("page_count", "1");
        d.field("label", &self.label.as_ref());
        d.close();
    }
}

pub struct Lockscreen<T> {
    label: T,
    bootscreen: bool,
}

impl<T> Lockscreen<T> {
    pub fn new(label: T, bootscreen: bool) -> Self {
        Lockscreen { label, bootscreen }
    }
}

impl<T> Component for Lockscreen<T>
where
    T: AsRef<str>,
{
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

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Lockscreen<T>
where
    T: AsRef<str>,
{
    fn trace(&self, d: &mut dyn crate::trace::Tracer) {
        d.open("Lockscreen");
        d.field("label", &self.label.as_ref());
        d.close();
    }
}
