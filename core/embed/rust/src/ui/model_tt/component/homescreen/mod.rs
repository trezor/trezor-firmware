mod render;

use crate::{
    micropython::gc::Gc,
    storage::{get_avatar, get_avatar_len},
    time::{Duration, Instant},
    trezorhal::usb::usb_configured,
    ui::{
        component::{Component, Event, EventCtx, Pad, TimerToken},
        display::{self, tjpgd::jpeg_info, toif::Icon, Color, Font},
        event::{TouchEvent, USBEvent},
        geometry::{Offset, Point, Rect},
        model_tt::{constant, theme::IMAGE_HOMESCREEN},
    },
};

use render::{
    homescreen, homescreen_blurred, HomescreenNotification, HomescreenText, HOMESCREEN_IMAGE_SIZE,
};

use super::{theme, Loader, LoaderMsg};

const AREA: Rect = constant::screen();
const TOP_CENTER: Point = AREA.top_center();
const LABEL_Y: i16 = 216;
const LOCKED_Y: i16 = 107;
const TAP_Y: i16 = 134;
const HOLD_Y: i16 = 35;
const LOADER_OFFSET: Offset = Offset::y(-10);
const LOADER_DELAY: Duration = Duration::from_millis(500);
const LOADER_DURATION: Duration = Duration::from_millis(2000);

pub struct Homescreen<T> {
    label: T,
    notification: Option<(T, u8)>,
    hold_to_lock: bool,
    loader: Loader,
    pad: Pad,
    paint_notification_only: bool,
    delay: Option<TimerToken>,
}

pub enum HomescreenMsg {
    Dismissed,
}

impl<T> Homescreen<T>
where
    T: AsRef<str>,
{
    pub fn new(label: T, notification: Option<(T, u8)>, hold_to_lock: bool) -> Self {
        Self {
            label,
            notification,
            hold_to_lock,
            loader: Loader::new().with_durations(LOADER_DURATION, LOADER_DURATION / 3),
            pad: Pad::with_background(theme::BG),
            paint_notification_only: false,
            delay: None,
        }
    }

    fn level_to_style(level: u8) -> (Color, Icon) {
        match level {
            2 => (theme::VIOLET, Icon::new(theme::ICON_MAGIC)),
            1 => (theme::YELLOW, Icon::new(theme::ICON_WARN)),
            _ => (theme::RED, Icon::new(theme::ICON_WARN)),
        }
    }

    fn get_notification(&self) -> Option<HomescreenNotification> {
        if !usb_configured() {
            let (color, icon) = Self::level_to_style(0);
            Some(HomescreenNotification {
                text: "NO USB CONNECTION",
                icon,
                color,
            })
        } else if let Some((notification, level)) = &self.notification {
            let (color, icon) = Self::level_to_style(*level);
            Some(HomescreenNotification {
                text: notification.as_ref(),
                icon,
                color,
            })
        } else {
            None
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

    pub fn set_paint_notification(&mut self) {
        self.paint_notification_only = true;
    }

    fn event_usb(&mut self, ctx: &mut EventCtx, event: Event) {
        if let Event::USB(USBEvent::Connected(_)) = event {
            self.paint_notification_only = true;
            ctx.request_paint();
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
                self.paint_notification_only = false;
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
                self.paint_notification_only = false;
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
            let mut label_style = theme::TEXT_BOLD;
            label_style.text_color = theme::FG;

            let text = HomescreenText {
                text: self.label.as_ref(),
                style: label_style,
                offset: Offset::new(10, LABEL_Y),
                icon: None,
            };

            let notification = self.get_notification();

            let res = get_image();
            if let Ok(data) = res {
                homescreen(
                    data.as_ref(),
                    &[text],
                    notification,
                    self.paint_notification_only,
                );
            } else {
                homescreen(
                    IMAGE_HOMESCREEN,
                    &[text],
                    notification,
                    self.paint_notification_only,
                );
            }
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

        let mut tap_style = theme::TEXT_NORMAL;
        tap_style.text_color = theme::OFF_WHITE;

        let mut label_style = theme::TEXT_BOLD;
        label_style.text_color = theme::GREY_LIGHT;

        let texts: [HomescreenText; 3] = [
            HomescreenText {
                text: locked,
                style: theme::TEXT_BOLD,
                offset: Offset::new(10, LOCKED_Y),
                icon: Some(Icon::new(theme::ICON_LOCK)),
            },
            HomescreenText {
                text: tap,
                style: tap_style,
                offset: Offset::new(10, TAP_Y),
                icon: None,
            },
            HomescreenText {
                text: self.label.as_ref(),
                style: label_style,
                offset: Offset::new(10, LABEL_Y),
                icon: None,
            },
        ];

        let res = get_image();
        if let Ok(data) = res {
            homescreen_blurred(data.as_ref(), &texts);
        } else {
            homescreen_blurred(IMAGE_HOMESCREEN, &texts);
        }
    }
}

fn get_image() -> Result<Gc<[u8]>, ()> {
    if let Ok(len) = get_avatar_len() {
        let result = Gc::<[u8]>::new_slice(len);
        if let Ok(mut buffer) = result {
            let buf = unsafe { Gc::<[u8]>::as_mut(&mut buffer) };
            if get_avatar(buf).is_ok() {
                let jpeg = jpeg_info(buffer.as_ref());
                if let Some((size, mcu_height)) = jpeg {
                    if size.x == HOMESCREEN_IMAGE_SIZE
                        && size.y == HOMESCREEN_IMAGE_SIZE
                        && mcu_height <= 16
                    {
                        return Ok(buffer);
                    }
                }
            }
        }
    };
    Err(())
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Lockscreen<T> {
    fn trace(&self, d: &mut dyn crate::trace::Tracer) {
        d.open("Lockscreen");
        d.close();
    }
}
