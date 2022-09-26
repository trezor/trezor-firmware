use crate::{
    time::{Duration, Instant},
    ui::{
        component::{Component, Empty, Event, EventCtx, Pad, TimerToken},
        display::{self, Color, Font},
        event::{TouchEvent, USBEvent},
        geometry::{Offset, Point, Rect},
        model_tt::constant,
        util::icon_text_center,
    },
};

use super::{theme, Loader, LoaderMsg, NotificationFrame};

const AREA: Rect = constant::screen();
const TOP_CENTER: Point = AREA.top_center();
const LABEL_Y: i16 = 216;
const LOCKED_Y: i16 = 101;
const TAP_Y: i16 = 134;
const HOLD_Y: i16 = 35;
const LOADER_OFFSET: Offset = Offset::y(-10);
const LOADER_DELAY: Duration = Duration::from_millis(500);
const LOADER_DURATION: Duration = Duration::from_millis(2000);

pub struct Homescreen<T> {
    label: T,
    notification: Option<(T, u32)>,
    hold_to_lock: bool,
    usb_connected: bool,
    loader: Loader,
    pad: Pad,
    delay: Option<TimerToken>,
}

pub enum HomescreenMsg {
    Dismissed,
}

impl<T> Homescreen<T>
where
    T: AsRef<str>,
{
    pub fn new(label: T, notification: Option<(T, u32)>, hold_to_lock: bool) -> Self {
        Self {
            label,
            notification,
            hold_to_lock,
            usb_connected: true,
            loader: Loader::new().with_durations(LOADER_DURATION, LOADER_DURATION / 3),
            pad: Pad::with_background(theme::BG),
            delay: None,
        }
    }

    fn level_to_style(level: u32) -> (Color, &'static [u8]) {
        match level {
            2 => (theme::VIOLET, theme::ICON_MAGIC),
            1 => (theme::YELLOW, theme::ICON_WARN),
            _ => (theme::RED, theme::ICON_WARN),
        }
    }

    fn paint_notification(&self) {
        if !self.usb_connected {
            let (color, icon) = Self::level_to_style(0);
            NotificationFrame::<Empty, T>::paint_notification(
                AREA,
                icon,
                "NO USB CONNECTION",
                color,
            );
        } else if let Some((notification, level)) = &self.notification {
            let (color, icon) = Self::level_to_style(*level);
            NotificationFrame::<Empty, T>::paint_notification(
                AREA,
                icon,
                notification.as_ref(),
                color,
            );
        }
    }

    fn paint_loader(&mut self) {
        display::text_center(
            TOP_CENTER + Offset::y(HOLD_Y),
            "HOLD TO LOCK",
            Font::BOLD,
            theme::FG,
            theme::BG,
        );
        self.loader.paint()
    }

    fn event_usb(&mut self, ctx: &mut EventCtx, event: Event) {
        if let Event::USB(USBEvent::Connected(is_connected)) = event {
            if self.usb_connected != is_connected {
                self.usb_connected = is_connected;
                ctx.request_paint();
            }
        }
    }

    fn event_hold(&mut self, ctx: &mut EventCtx, event: Event) -> bool {
        match event {
            Event::Touch(TouchEvent::TouchStart(_)) => {
                if self.loader.is_animating() {
                    self.loader.start_growing(ctx, Instant::now());
                } else {
                    self.delay = Some(ctx.request_timer(LOADER_DELAY));
                }
            }
            Event::Touch(TouchEvent::TouchEnd(_)) => {
                self.delay = None;
                let now = Instant::now();
                if self.loader.is_completely_grown(now) {
                    return true;
                }
                if self.loader.is_animating() {
                    self.loader.start_shrinking(ctx, now);
                }
            }
            Event::Timer(token) if Some(token) == self.delay => {
                self.delay = None;
                self.pad.clear();
                self.loader.start_growing(ctx, Instant::now());
            }
            _ => {}
        }

        match self.loader.event(ctx, event) {
            Some(LoaderMsg::GrownCompletely) => {
                // Wait for TouchEnd before returning.
            }
            Some(LoaderMsg::ShrunkCompletely) => {
                self.loader.reset();
                self.pad.clear();
                ctx.request_paint()
            }
            None => {}
        }

        false
    }
}

impl<T> Component for Homescreen<T>
where
    T: AsRef<str>,
{
    type Msg = HomescreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.pad.place(AREA);
        self.loader.place(AREA.translate(LOADER_OFFSET));
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        Self::event_usb(self, ctx, event);
        if self.hold_to_lock {
            Self::event_hold(self, ctx, event).then_some(HomescreenMsg::Dismissed)
        } else {
            None
        }
    }

    fn paint(&mut self) {
        self.pad.paint();
        if self.loader.is_animating() || self.loader.is_completely_grown(Instant::now()) {
            self.paint_loader();
        } else {
            self.paint_notification();
            paint_label(self.label.as_ref(), false);
        }
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.loader.bounds(sink);
        sink(self.pad.area);
    }
}

#[cfg(feature = "ui_debug")]
impl<T: AsRef<str>> crate::trace::Trace for Homescreen<T> {
    fn trace(&self, d: &mut dyn crate::trace::Tracer) {
        d.open("Homescreen");
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
        if let Event::Touch(TouchEvent::TouchEnd(_)) = event {
            return Some(HomescreenMsg::Dismissed);
        }
        None
    }

    fn paint(&mut self) {
        let (locked, tap) = if self.bootscreen {
            ("NOT CONNECTED", "Tap to connect")
        } else {
            ("LOCKED", "Tap to unlock")
        };
        icon_text_center(
            TOP_CENTER + Offset::y(LOCKED_Y),
            theme::ICON_LOCK,
            2,
            locked,
            theme::TEXT_BOLD,
            Offset::zero(),
        );
        display::text_center(
            TOP_CENTER + Offset::y(TAP_Y),
            tap,
            Font::NORMAL,
            theme::OFF_WHITE,
            theme::BG,
        );
        paint_label(self.label.as_ref(), true);
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Lockscreen<T> {
    fn trace(&self, d: &mut dyn crate::trace::Tracer) {
        d.open("Lockscreen");
        d.close();
    }
}

fn paint_label(label: &str, lockscreen: bool) {
    let label_color = if lockscreen {
        theme::GREY_MEDIUM
    } else {
        theme::FG
    };
    display::text_center(
        TOP_CENTER + Offset::y(LABEL_Y),
        label,
        Font::BOLD,
        label_color,
        theme::BG,
    );
}
