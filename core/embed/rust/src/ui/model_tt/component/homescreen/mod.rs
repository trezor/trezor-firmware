mod render;

use heapless::String;
use crate::{
    time::{Duration, Instant},
    trezorhal::usb::usb_configured,
    ui::{
        component::{Component, Event, EventCtx, Pad, TimerToken},
        display::{self, tjpgd::jpeg_info, toif::Icon, Color, Font},
        event::{TouchEvent, USBEvent},
        geometry::{Offset, Point, Rect},
        layout::util::get_user_custom_image,
        model_tt::{constant, theme::IMAGE_HOMESCREEN},
    },
};

use crate::{
    trezorhal::{buffers::BufferJpegWork, display::ToifFormat, uzlib::UZLIB_WINDOW_SIZE},
    ui::{
        constant::HEIGHT,
        display::{tjpgd::BufferInput, toif::Toif},
        model_tt::component::homescreen::render::{
            HomescreenJpeg, HomescreenToif, HOMESCREEN_TOIF_SIZE,
        },
    },
};
use render::{
    homescreen, homescreen_blurred, HomescreenNotification, HomescreenText,
    HOMESCREEN_IMAGE_HEIGHT, HOMESCREEN_IMAGE_WIDTH,
};
use crate::trezorhal::haptic;
use crate::ui::component::ComponentExt;
use crate::ui::model_tt::component::{PinKeyboard, PinKeyboardMsg};

use super::{theme, Loader, LoaderMsg};

const AREA: Rect = constant::screen();
const TOP_CENTER: Point = AREA.top_center();
const LABEL_Y: i16 = HEIGHT - 18;
const LOCKED_Y: i16 = HEIGHT / 2 - 13;
const TAP_Y: i16 = HEIGHT / 2 + 14;
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
    pin: bool,
    delay: Option<TimerToken>,
    kbd: PinKeyboard<&'static str>,
    effect: u8,
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
            pin: false,
            kbd: PinKeyboard::new("Enter effect num", "", None, true),
            effect: 1,
        }
    }

    fn level_to_style(level: u8) -> (Color, Icon) {
        match level {
            3 => (theme::YELLOW, theme::ICON_COINJOIN),
            2 => (theme::VIOLET, theme::ICON_MAGIC),
            1 => (theme::YELLOW, theme::ICON_WARN),
            _ => (theme::RED, theme::ICON_WARN),
        }
    }

    fn get_notification<'a>(&'a self, s: &'a mut String<20>) -> Option<HomescreenNotification> {

        let (color, icon) = Self::level_to_style(0);
        unwrap!(s.push_str("Effect: "));
        unwrap!(s.push_str(inttostr!(self.effect)));
        Some(HomescreenNotification {
            text: s.as_str(),
            icon,
            color,
        })

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
        self.kbd.place(AREA);
        self.loader.place(AREA.translate(LOADER_OFFSET));
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {

        if let Event::Touch(TouchEvent::TouchStart(_)) = event {
            haptic::play(self.effect);

            if !self.pin{
            self.pin= true;
            self.kbd.clear(ctx);
            self.pad.clear();
            ctx.request_paint();
            self.request_complete_repaint(ctx);
            return None;
            }
        }

        if self.pin {
            if let Some(e)=self.kbd.event(ctx, event) {
                match e {
                    PinKeyboardMsg::Confirmed => {
                        let pin = self.kbd.pin();
                        pin.parse().ok().map(|pin :u32| {
                            if pin <= 123 {
                                if pin == 0 {
                                    self.effect = 1;
                                } else {
                                    self.effect = pin as u8;
                                }
                            }
                            self.pin = false;
                        });
                        self.pad.clear();
                        self.pin = false;
                        ctx.request_paint();
                        self.request_complete_repaint(ctx);
                    }
                    PinKeyboardMsg::Cancelled => {
                        self.pin = false;
                        self.pad.clear();
                        ctx.request_paint();
                        self.request_complete_repaint(ctx);
                    }
                }
            }
            None
        }else {
            Self::event_usb(self, ctx, event);
            if self.hold_to_lock {
                Self::event_hold(self, ctx, event).then_some(HomescreenMsg::Dismissed)
            } else {
                None
            }
        }
    }

    fn paint(&mut self) {
        self.pad.paint();
        if self.pin {
            self.kbd.paint();
        } else if self.loader.is_animating() || self.loader.is_completely_grown(Instant::now()) {
            self.paint_loader();
        } else {
            let mut label_style = theme::TEXT_DEMIBOLD;
            label_style.text_color = theme::FG;

            let text = HomescreenText {
                text: self.label.as_ref(),
                style: label_style,
                offset: Offset::new(10, LABEL_Y),
                icon: None,
            };


            let mut s: String<20> = String::new();
            let notification = self.get_notification(&mut s);

            let res = get_user_custom_image();
            let mut show_default = true;

            if let Ok(data) = res {
                if is_image_jpeg(data.as_ref()) {
                    let mut input = BufferInput(data.as_ref());
                    let mut pool = BufferJpegWork::get_cleared();
                    let mut hs_img = HomescreenJpeg::new(&mut input, pool.buffer.as_mut_slice());
                    homescreen(
                        &mut hs_img,
                        &[text],
                        notification,
                        self.paint_notification_only,
                    );
                    show_default = false;
                } else if is_image_toif(data.as_ref()) {
                    let input = unwrap!(Toif::new(data.as_ref()));
                    let mut window = [0; UZLIB_WINDOW_SIZE];
                    let mut hs_img =
                        HomescreenToif::new(input.decompression_context(Some(&mut window)));
                    homescreen(
                        &mut hs_img,
                        &[text],
                        notification,
                        self.paint_notification_only,
                    );
                    show_default = false;
                }
            }

            if show_default {
                let mut input = BufferInput(IMAGE_HOMESCREEN);
                let mut pool = BufferJpegWork::get_cleared();
                let mut hs_img = HomescreenJpeg::new(&mut input, pool.buffer.as_mut_slice());
                homescreen(
                    &mut hs_img,
                    &[text],
                    notification,
                    self.paint_notification_only,
                );
            }
        }
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.loader.bounds(sink);
        sink(self.pad.area);
    }
}

#[cfg(feature = "ui_debug")]
impl<T: AsRef<str>> crate::trace::Trace for Homescreen<T> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Homescreen");
        t.string("label", self.label.as_ref());
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

        let mut label_style = theme::TEXT_DEMIBOLD;
        label_style.text_color = theme::GREY_LIGHT;

        let texts: [HomescreenText; 3] = [
            HomescreenText {
                text: locked,
                style: theme::TEXT_BOLD,
                offset: Offset::new(10, LOCKED_Y),
                icon: Some(theme::ICON_LOCK),
            },
            HomescreenText {
                text: tap,
                style: theme::TEXT_NORMAL,
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

        let res = get_user_custom_image();
        let mut show_default = true;

        if let Ok(data) = res {
            if is_image_jpeg(data.as_ref()) {
                let mut input = BufferInput(data.as_ref());
                let mut pool = BufferJpegWork::get_cleared();
                let mut hs_img = HomescreenJpeg::new(&mut input, pool.buffer.as_mut_slice());
                homescreen_blurred(&mut hs_img, &texts);
                show_default = false;
            } else if is_image_toif(data.as_ref()) {
                let input = unwrap!(Toif::new(data.as_ref()));
                let mut window = [0; UZLIB_WINDOW_SIZE];
                let mut hs_img =
                    HomescreenToif::new(input.decompression_context(Some(&mut window)));
                homescreen_blurred(&mut hs_img, &texts);
                show_default = false;
            }
        }

        if show_default {
            let mut input = BufferInput(IMAGE_HOMESCREEN);
            let mut pool = BufferJpegWork::get_cleared();
            let mut hs_img = HomescreenJpeg::new(&mut input, pool.buffer.as_mut_slice());
            homescreen_blurred(&mut hs_img, &texts);
        }
    }
}

fn is_image_jpeg(buffer: &[u8]) -> bool {
    let jpeg = jpeg_info(buffer);
    if let Some((size, mcu_height)) = jpeg {
        if size.x == HOMESCREEN_IMAGE_WIDTH && size.y == HOMESCREEN_IMAGE_HEIGHT && mcu_height <= 16
        {
            return true;
        }
    }
    false
}

fn is_image_toif(buffer: &[u8]) -> bool {
    let toif = Toif::new(buffer);
    if let Some(toif) = toif {
        if toif.size().x == HOMESCREEN_TOIF_SIZE
            && toif.size().y == HOMESCREEN_TOIF_SIZE
            && toif.format() == ToifFormat::FullColorBE
        {
            return true;
        }
    }
    false
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Lockscreen<T> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Lockscreen");
    }
}
