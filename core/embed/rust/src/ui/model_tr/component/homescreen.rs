use crate::{
    micropython::{buffer::StrBuffer, gc::Gc},
    storage::{get_avatar, get_avatar_len},
    trezorhal::usb::usb_configured,
    ui::{
        component::{Child, Component, Event, EventCtx, Pad},
        display::{
            fill_background_for_text, rect_fill,
            toif::{icon_from_toif, Toif},
            Font, Icon,
        },
        event::USBEvent,
        geometry::{self, Alignment, Offset, Point, Rect},
    },
};

use super::{
    super::constant, common::display_center, theme, ButtonController, ButtonControllerMsg,
    ButtonLayout,
};

const AREA: Rect = constant::screen();
const TOP_CENTER: Point = AREA.top_center();
const LABEL_Y: i16 = constant::HEIGHT - 5;
const LOCKED_INSTRUCTION_Y: i16 = 34;
const LOGO_ICON_TOP_MARGIN: i16 = 12;
const LOCK_ICON_TOP_MARGIN: i16 = 12;
const NOTIFICATION_HEIGHT: i16 = 12;

pub struct Homescreen {
    label: StrBuffer,
    notification: Option<(StrBuffer, u8)>,
    pad: Pad,
    /// Used for HTC functionality to lock device from homescreen
    invisible_buttons: Child<ButtonController<StrBuffer>>,
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
        // Filling the background to be well visible even on homescreen image
        let baseline = TOP_CENTER + Offset::y(Font::MONO.line_height());
        if !usb_configured() {
            rect_fill(AREA.split_top(NOTIFICATION_HEIGHT).0, theme::BG);
            // TODO: fill warning icons here as well?
            display_center(baseline, &"NO USB CONNECTION", Font::MONO);
        } else if let Some((notification, _level)) = &self.notification {
            rect_fill(AREA.split_top(NOTIFICATION_HEIGHT).0, theme::BG);
            display_center(baseline, &notification.as_ref(), Font::MONO);
            // TODO: what if the notification text is so long it collides with icons?
            let warning_icon = Icon::new(theme::ICON_WARNING);
            warning_icon.draw(AREA.top_left(), geometry::TOP_LEFT, theme::FG, theme::BG);
            // Needs x+1 Offset to compensate for empty right column (icon needs to be
            // even-wide)
            warning_icon.draw(
                AREA.top_right() + Offset::x(1),
                geometry::TOP_RIGHT,
                theme::FG,
                theme::BG,
            );
        }
    }

    fn paint_label(&self) {
        let label = self.label.as_ref();
        let baseline = TOP_CENTER + Offset::y(LABEL_Y);
        fill_background_for_text(
            baseline,
            label,
            Font::NORMAL,
            theme::BG,
            Alignment::Center,
            3,
        );
        display_center(baseline, &label, Font::NORMAL);
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
        // Painting the homescreen image first, as the notification and label
        // should be "on top of it"
        if let Ok(user_custom_image) = get_user_custom_image() {
            // TODO: how to make it better? I did not want to introduce lifetime to
            // `Icon`, it would then need to be specified in a lot of places.
            let toif_data = unwrap!(Toif::new(user_custom_image.as_ref()));
            let r = Rect::snap(TOP_CENTER, toif_data.size(), geometry::TOP_CENTER);
            icon_from_toif(&toif_data, r.center(), theme::FG, theme::BG);
        } else {
            Icon::new(theme::ICON_LOGO).draw(
                TOP_CENTER + Offset::y(LOGO_ICON_TOP_MARGIN),
                geometry::TOP_CENTER,
                theme::FG,
                theme::BG,
            );
        }

        self.paint_notification();
        self.paint_label();
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.pad.area);
    }
}

// TODO: this is copy-paste from `model_tt/component/homescreen/mod.rs`,
// probably could be moved to some common place (maybe storage)
fn get_user_custom_image() -> Result<Gc<[u8]>, ()> {
    if let Ok(len) = get_avatar_len() {
        let result = Gc::<[u8]>::new_slice(len);
        if let Ok(mut buffer) = result {
            let buf = unsafe { Gc::<[u8]>::as_mut(&mut buffer) };
            if get_avatar(buf).is_ok() {
                return Ok(buffer);
            }
        }
    };
    Err(())
}

pub struct Lockscreen {
    label: StrBuffer,
    bootscreen: bool,
    /// Used for unlocking the device from lockscreen
    invisible_buttons: Child<ButtonController<StrBuffer>>,
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
            "Click to Connect"
        } else {
            "Click to Unlock"
        };
        display_center(
            TOP_CENTER + Offset::y(LOCKED_INSTRUCTION_Y),
            &instruction,
            Font::MONO,
        );
        Icon::new(theme::ICON_LOCK).draw(
            TOP_CENTER + Offset::y(LOCK_ICON_TOP_MARGIN),
            geometry::TOP_CENTER,
            theme::FG,
            theme::BG,
        );
        display_center(
            TOP_CENTER + Offset::y(LABEL_Y),
            &self.label.as_ref(),
            Font::NORMAL,
        );
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Homescreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Homescreen");
        t.string("label", self.label.as_ref());
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Lockscreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Lockscreen");
        t.string("label", self.label.as_ref());
    }
}
