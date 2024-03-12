mod render;

use crate::{
    micropython::gc::Gc,
    strutil::TString,
    time::{Duration, Instant},
    translations::TR,
    trezorhal::usb::usb_configured,
    ui::{
        component::{Component, Event, EventCtx, Pad, TimerToken},
        display::{self, tjpgd::jpeg_info, toif::Icon, Color, Font},
        event::{TouchEvent, USBEvent},
        geometry::{Alignment, Alignment2D, Insets, Offset, Point, Rect},
        layout::util::get_user_custom_image,
        model_tt::{constant, theme::IMAGE_HOMESCREEN},
        shape::{self, Renderer},
    },
};

use crate::{
    trezorhal::{buffers::BufferJpegWork, uzlib::UZLIB_WINDOW_SIZE},
    ui::{
        constant::HEIGHT,
        display::{
            tjpgd::BufferInput,
            toif::{Toif, ToifFormat},
        },
        model_tt::component::homescreen::render::{
            HomescreenJpeg, HomescreenToif, HOMESCREEN_TOIF_SIZE,
        },
    },
};
use render::{
    homescreen, homescreen_blurred, HomescreenNotification, HomescreenText,
    HOMESCREEN_IMAGE_HEIGHT, HOMESCREEN_IMAGE_WIDTH,
};

use super::{theme, Loader, LoaderMsg};

const AREA: Rect = constant::screen();
const TOP_CENTER: Point = AREA.top_center();
const LABEL_Y: i16 = HEIGHT - 18;
const LOCKED_Y: i16 = HEIGHT / 2 - 13;
const TAP_Y: i16 = HEIGHT / 2 + 14;
const HOLD_Y: i16 = 200;
const COINJOIN_Y: i16 = 30;
const LOADER_OFFSET: Offset = Offset::y(-10);
const LOADER_DELAY: Duration = Duration::from_millis(500);
const LOADER_DURATION: Duration = Duration::from_millis(2000);

pub struct Homescreen {
    label: TString<'static>,
    notification: Option<(TString<'static>, u8)>,
    custom_image: Option<Gc<[u8]>>,
    hold_to_lock: bool,
    loader: Loader,
    pad: Pad,
    paint_notification_only: bool,
    delay: Option<TimerToken>,
}

pub enum HomescreenMsg {
    Dismissed,
}

impl Homescreen {
    pub fn new(
        label: TString<'static>,
        notification: Option<(TString<'static>, u8)>,
        hold_to_lock: bool,
    ) -> Self {
        Self {
            label,
            notification,
            custom_image: get_user_custom_image().ok(),
            hold_to_lock,
            loader: Loader::with_lock_icon().with_durations(LOADER_DURATION, LOADER_DURATION / 3),
            pad: Pad::with_background(theme::BG),
            paint_notification_only: false,
            delay: None,
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

    fn get_notification(&self) -> Option<HomescreenNotification> {
        if !usb_configured() {
            let (color, icon) = Self::level_to_style(0);
            Some(HomescreenNotification {
                text: TR::homescreen__title_no_usb_connection.into(),
                icon,
                color,
            })
        } else if let Some((notification, level)) = self.notification {
            let (color, icon) = Self::level_to_style(level);
            Some(HomescreenNotification {
                text: notification,
                icon,
                color,
            })
        } else {
            None
        }
    }

    fn paint_loader(&mut self) {
        TR::progress__locking_device.map_translated(|t| {
            display::text_center(
                TOP_CENTER + Offset::y(HOLD_Y),
                t,
                Font::NORMAL,
                theme::FG,
                theme::BG,
            )
        });
        self.loader.paint()
    }

    fn render_loader<'s>(&'s self, target: &mut impl Renderer<'s>) {
        TR::progress__locking_device.map_translated(|t| {
            shape::Text::new(TOP_CENTER + Offset::y(HOLD_Y), t)
                .with_align(Alignment::Center)
                .with_font(Font::NORMAL)
                .with_fg(theme::FG);
        });
        self.loader.render(target)
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

impl Component for Homescreen {
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
            let mut label_style = theme::TEXT_DEMIBOLD;
            label_style.text_color = theme::FG;

            let text = HomescreenText {
                text: self.label,
                style: label_style,
                offset: Offset::y(LABEL_Y),
                icon: None,
            };

            let notification = self.get_notification();

            let mut show_default = true;

            if let Some(ref data) = self.custom_image {
                if is_image_jpeg(data.as_ref()) {
                    let input = BufferInput(data.as_ref());
                    let mut pool = BufferJpegWork::get_cleared();
                    let mut hs_img = HomescreenJpeg::new(input, pool.buffer.as_mut_slice());
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
                let input = BufferInput(IMAGE_HOMESCREEN);
                let mut pool = BufferJpegWork::get_cleared();
                let mut hs_img = HomescreenJpeg::new(input, pool.buffer.as_mut_slice());
                homescreen(
                    &mut hs_img,
                    &[text],
                    notification,
                    self.paint_notification_only,
                );
            }
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.pad.render(target);
        if self.loader.is_animating() || self.loader.is_completely_grown(Instant::now()) {
            self.render_loader(target);
        } else {
            let img_data = match self.custom_image {
                Some(ref img) => img.as_ref(),
                None => IMAGE_HOMESCREEN,
            };

            if is_image_jpeg(img_data) {
                shape::JpegImage::new(self.pad.area.center(), img_data)
                    .with_align(Alignment2D::CENTER)
                    .render(target);
            } else if is_image_toif(img_data) {
                shape::ToifImage::new(self.pad.area.center(), unwrap!(Toif::new(img_data)))
                    .with_align(Alignment2D::CENTER)
                    .render(target);
            }

            self.label.map(|t| {
                let r = Rect::new(Point::new(6, 198), Point::new(234, 233));
                shape::Bar::new(r)
                    .with_bg(Color::black())
                    .with_alpha(89)
                    .with_radius(3)
                    .render(target);

                let style = theme::TEXT_DEMIBOLD;
                let pos = Point::new(self.pad.area.center().x, LABEL_Y);
                shape::Text::new(pos, t)
                    .with_align(Alignment::Center)
                    .with_font(style.text_font)
                    .with_fg(theme::FG)
                    .render(target);
            });

            if let Some(notif) = self.get_notification() {
                const NOTIFICATION_HEIGHT: i16 = 36;
                const NOTIFICATION_BORDER: i16 = 6;
                const TEXT_ICON_SPACE: i16 = 8;

                let banner = self
                    .pad
                    .area
                    .inset(Insets::sides(NOTIFICATION_BORDER))
                    .with_height(NOTIFICATION_HEIGHT)
                    .translate(Offset::y(NOTIFICATION_BORDER));

                shape::Bar::new(banner)
                    .with_radius(2)
                    .with_bg(notif.color)
                    .render(target);

                notif.text.map(|t| {
                    let style = theme::TEXT_BOLD;
                    let icon_width = notif.icon.toif.width() + TEXT_ICON_SPACE;
                    let text_pos = Point::new(
                        style
                            .text_font
                            .horz_center(banner.x0 + icon_width, banner.x1, t),
                        style.text_font.vert_center(banner.y0, banner.y1, "A"),
                    );

                    shape::Text::new(text_pos, t)
                        .with_font(style.text_font)
                        .with_fg(style.text_color)
                        .render(target);

                    let icon_pos = Point::new(text_pos.x - icon_width, banner.center().y);

                    shape::ToifImage::new(icon_pos, notif.icon.toif)
                        .with_fg(style.text_color)
                        .with_align(Alignment2D::CENTER_LEFT)
                        .render(target);
                });
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
impl crate::trace::Trace for Homescreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Homescreen");
        t.string("label", self.label);
    }
}

pub struct Lockscreen {
    label: TString<'static>,
    custom_image: Option<Gc<[u8]>>,
    bootscreen: bool,
    coinjoin_authorized: bool,
}

impl Lockscreen {
    pub fn new(label: TString<'static>, bootscreen: bool, coinjoin_authorized: bool) -> Self {
        Lockscreen {
            label,
            custom_image: get_user_custom_image().ok(),
            bootscreen,
            coinjoin_authorized,
        }
    }
}

impl Component for Lockscreen {
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
            (
                TR::lockscreen__title_not_connected,
                TR::lockscreen__tap_to_connect,
            )
        } else {
            (TR::lockscreen__title_locked, TR::lockscreen__tap_to_unlock)
        };

        let mut label_style = theme::TEXT_DEMIBOLD;
        label_style.text_color = theme::GREY_LIGHT;

        let mut texts: &[HomescreenText] = &[
            HomescreenText {
                text: "".into(),
                style: theme::TEXT_NORMAL,
                offset: Offset::new(2, COINJOIN_Y),
                icon: Some(theme::ICON_COINJOIN),
            },
            HomescreenText {
                text: locked.into(),
                style: theme::TEXT_BOLD,
                offset: Offset::y(LOCKED_Y),
                icon: Some(theme::ICON_LOCK),
            },
            HomescreenText {
                text: tap.into(),
                style: theme::TEXT_NORMAL,
                offset: Offset::y(TAP_Y),
                icon: None,
            },
            HomescreenText {
                text: self.label,
                style: label_style,
                offset: Offset::y(LABEL_Y),
                icon: None,
            },
        ];

        if !self.coinjoin_authorized {
            texts = &texts[1..];
        }

        let mut show_default = true;

        if let Some(ref data) = self.custom_image {
            if is_image_jpeg(data.as_ref()) {
                let input = BufferInput(data.as_ref());
                let mut pool = BufferJpegWork::get_cleared();
                let mut hs_img = HomescreenJpeg::new(input, pool.buffer.as_mut_slice());
                homescreen_blurred(&mut hs_img, texts);
                show_default = false;
            } else if is_image_toif(data.as_ref()) {
                let input = unwrap!(Toif::new(data.as_ref()));
                let mut window = [0; UZLIB_WINDOW_SIZE];
                let mut hs_img =
                    HomescreenToif::new(input.decompression_context(Some(&mut window)));
                homescreen_blurred(&mut hs_img, texts);
                show_default = false;
            }
        }

        if show_default {
            let input = BufferInput(IMAGE_HOMESCREEN);
            let mut pool = BufferJpegWork::get_cleared();
            let mut hs_img = HomescreenJpeg::new(input, pool.buffer.as_mut_slice());
            homescreen_blurred(&mut hs_img, texts);
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let img_data = match self.custom_image {
            Some(ref img) => img.as_ref(),
            None => IMAGE_HOMESCREEN,
        };

        let center = constant::screen().center();

        if is_image_jpeg(img_data) {
            shape::JpegImage::new(center, img_data)
                .with_align(Alignment2D::CENTER)
                .with_blur(4)
                .with_dim(140)
                .render(target);
        } else if is_image_toif(img_data) {
            shape::ToifImage::new(center, unwrap!(Toif::new(img_data)))
                .with_align(Alignment2D::CENTER)
                //.with_blur(5)
                .render(target);
        }

        let (locked, tap) = if self.bootscreen {
            (
                TR::lockscreen__title_not_connected,
                TR::lockscreen__tap_to_connect,
            )
        } else {
            (TR::lockscreen__title_locked, TR::lockscreen__tap_to_unlock)
        };

        let mut label_style = theme::TEXT_DEMIBOLD;
        label_style.text_color = theme::GREY_LIGHT;

        let mut texts: &[HomescreenText] = &[
            HomescreenText {
                text: "".into(),
                style: theme::TEXT_NORMAL,
                offset: Offset::new(2, COINJOIN_Y),
                icon: Some(theme::ICON_COINJOIN),
            },
            HomescreenText {
                text: locked.into(),
                style: theme::TEXT_BOLD,
                offset: Offset::y(LOCKED_Y),
                icon: Some(theme::ICON_LOCK),
            },
            HomescreenText {
                text: tap.into(),
                style: theme::TEXT_NORMAL,
                offset: Offset::y(TAP_Y),
                icon: None,
            },
            HomescreenText {
                text: self.label,
                style: label_style,
                offset: Offset::y(LABEL_Y),
                icon: None,
            },
        ];

        if !self.coinjoin_authorized {
            texts = &texts[1..];
        }

        for item in texts.iter() {
            item.text.map(|t| {
                const TEXT_ICON_SPACE: i16 = 2;

                let icon_width = match item.icon {
                    Some(icon) => icon.toif.width() + TEXT_ICON_SPACE,
                    None => 0,
                };

                let area = constant::screen();

                let text_pos = Point::new(
                    item.style
                        .text_font
                        .horz_center(area.x0 + icon_width, area.x1, t),
                    0,
                ) + item.offset;

                shape::Text::new(text_pos, t)
                    .with_font(item.style.text_font)
                    .with_fg(item.style.text_color)
                    .render(target);

                if let Some(icon) = item.icon {
                    let icon_pos = Point::new(text_pos.x - icon_width, text_pos.y);
                    shape::ToifImage::new(icon_pos, icon.toif)
                        .with_align(Alignment2D::BOTTOM_LEFT)
                        .with_fg(item.style.text_color)
                        .render(target);
                }
            });
        }
    }
}

pub fn check_homescreen_format(buffer: &[u8]) -> bool {
    #[cfg(not(feature = "new_rendering"))]
    let result = is_image_jpeg(buffer) && crate::ui::display::tjpgd::jpeg_test(buffer);
    #[cfg(feature = "new_rendering")]
    let result = is_image_jpeg(buffer); // !@# TODO: test like if `new_rendering` is off

    result
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
    if let Ok(toif) = toif {
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
impl crate::trace::Trace for Lockscreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Lockscreen");
    }
}
