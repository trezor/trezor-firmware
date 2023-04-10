use crate::{
    micropython::buffer::StrBuffer,
    trezorhal::usb::usb_configured,
    ui::{
        component::{Child, Component, Event, EventCtx, Pad},
        display::{Font, Icon},
        event::USBEvent,
        geometry::{self, Offset, Point, Rect},
        model_tr::constant,
        util::icon_text_center,
    },
};

use super::{common::display_center, theme, ButtonController, ButtonControllerMsg, ButtonLayout};

const AREA: Rect = constant::screen();
const TOP_CENTER: Point = AREA.top_center();
const LABEL_Y: i16 = 62;
const ICON_TOP_MARGIN: i16 = 11;

pub struct Homescreen {
    label: StrBuffer,
    notification: Option<(StrBuffer, u8)>,
    pad: Pad,
    /// Used for HTC functionality to lock device from homescreen
    invisible_buttons: Child<ButtonController>,
}

pub enum HomescreenMsg {
    Dismissed,
}

impl Homescreen {
    pub fn new(label: StrBuffer, notification: Option<(StrBuffer, u8)>) -> Self {
        // NOTE: for some reason the text cannot be empty string, it was panicking at
        // library/core/src/str/mod.rs:107
        let invisible_btn_layout = ButtonLayout::htc_none_htc("_".into(), "_".into());
        Self {
            label,
            notification,
            pad: Pad::with_background(theme::BG),
            invisible_buttons: Child::new(ButtonController::new(invisible_btn_layout)),
        }
    }

    fn paint_notification(&self) {
        let baseline = TOP_CENTER + Offset::y(Font::MONO.line_height());
        if !usb_configured() {
            display_center(baseline, &"NO USB CONNECTION", Font::MONO);
        } else if let Some((notification, _level)) = &self.notification {
            display_center(baseline, &notification.as_ref(), Font::MONO);
        }
    }

    fn event_usb(&mut self, ctx: &mut EventCtx, event: Event) {
        if let Event::USB(USBEvent::Connected(_)) = event {
            ctx.request_paint();
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
        // HTC press of any button will lock the device
        if let Some(ButtonControllerMsg::Triggered(_)) = self.invisible_buttons.event(ctx, event) {
            return Some(HomescreenMsg::Dismissed);
        }
        None
    }

    fn paint(&mut self) {
        self.pad.paint();
        self.paint_notification();
        // TODO: support users to set their own homscreens?
        Icon::new(theme::ICON_LOGO).draw(
            TOP_CENTER + Offset::y(ICON_TOP_MARGIN),
            geometry::TOP_CENTER,
            theme::FG,
            theme::BG,
        );
        let label = self.label.as_ref();
        // Special case for the initial screen label
        if label == "Go to trezor.io/start" {
            display_center(TOP_CENTER + Offset::y(54), &"Go to", Font::BOLD);
            display_center(TOP_CENTER + Offset::y(64), &"trezor.io/start", Font::BOLD);
        } else {
            display_center(TOP_CENTER + Offset::y(LABEL_Y), &label, Font::NORMAL);
        };
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.pad.area);
    }
}

pub struct Lockscreen {
    label: StrBuffer,
    bootscreen: bool,
    /// Used for unlocking the device from lockscreen
    invisible_buttons: Child<ButtonController>,
}

impl Lockscreen {
    pub fn new(label: StrBuffer, bootscreen: bool) -> Self {
        let invisible_btn_layout = ButtonLayout::text_none_text("_".into(), "_".into());
        Lockscreen {
            label,
            bootscreen,
            invisible_buttons: Child::new(ButtonController::new(invisible_btn_layout)),
        }
    }
}

impl Component for Lockscreen {
    type Msg = HomescreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Press of any button will unlock the device
        if let Some(ButtonControllerMsg::Triggered(_)) = self.invisible_buttons.event(ctx, event) {
            return Some(HomescreenMsg::Dismissed);
        }
        None
    }

    fn paint(&mut self) {
        let instruction = if self.bootscreen {
            "CLICK TO CONNECT"
        } else {
            "CLICK TO UNLOCK"
        };
        display_center(
            TOP_CENTER + Offset::y(Font::MONO.line_height()),
            &instruction,
            Font::MONO,
        );
        Icon::new(theme::ICON_LOGO).draw(
            TOP_CENTER + Offset::y(ICON_TOP_MARGIN),
            geometry::TOP_CENTER,
            theme::FG,
            theme::BG,
        );
        icon_text_center(
            TOP_CENTER + Offset::y(LABEL_Y - Font::NORMAL.text_height() / 2),
            Icon::new(theme::ICON_LOCK),
            4,
            self.label.as_ref(),
            theme::TEXT_NORMAL,
            Offset::zero(),
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
