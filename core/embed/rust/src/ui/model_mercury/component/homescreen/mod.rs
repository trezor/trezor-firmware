use crate::{
    io::BinaryData,
    strutil::TString,
    time::{Duration, Instant},
    translations::TR,
    trezorhal::usb::usb_configured,
    ui::{
        component::{Component, Event, EventCtx, TimerToken},
        display::{
            image::{ImageInfo, ToifFormat},
            toif::Icon,
            Color, Font,
        },
        event::{TouchEvent, USBEvent},
        geometry::{Alignment, Alignment2D, Insets, Offset, Point, Rect},
        layout::util::get_user_custom_image,
        model_mercury::{constant, theme::IMAGE_HOMESCREEN},
        shape::{self, Renderer},
    },
};

use crate::ui::{
    constant::{screen, HEIGHT, WIDTH},
    model_mercury::theme::{
        GREEN_LIGHT, GREY_LIGHT, ICON_CENTRAL_CIRCLE, ICON_KEY, ICON_LOCKSCREEN_FILTER,
    },
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

pub const HOMESCREEN_IMAGE_WIDTH: i16 = WIDTH;
pub const HOMESCREEN_IMAGE_HEIGHT: i16 = HEIGHT;
pub const HOMESCREEN_TOIF_SIZE: i16 = 144;

#[derive(Clone, Copy)]
pub struct HomescreenNotification {
    pub text: TString<'static>,
    pub icon: Icon,
    pub color: Color,
}

pub struct Homescreen {
    label: TString<'static>,
    notification: Option<(TString<'static>, u8)>,
    image: BinaryData<'static>,
    hold_to_lock: bool,
    loader: Loader,
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
            image: get_homescreen_image(),
            hold_to_lock,
            loader: Loader::with_lock_icon().with_durations(LOADER_DURATION, LOADER_DURATION / 3),
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

    fn render_loader<'s>(&'s self, target: &mut impl Renderer<'s>) {
        TR::progress__locking_device.map_translated(|t| {
            shape::Text::new(TOP_CENTER + Offset::y(HOLD_Y), t)
                .with_align(Alignment::Center)
                .with_font(Font::NORMAL)
                .with_fg(theme::FG);
        });
        self.loader.render(target)
    }

    fn event_usb(&mut self, ctx: &mut EventCtx, event: Event) {
        if let Event::USB(USBEvent::Connected(_)) = event {
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
        todo!()
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if self.loader.is_animating() || self.loader.is_completely_grown(Instant::now()) {
            self.render_loader(target);
        } else {
            match ImageInfo::parse(self.image) {
                ImageInfo::Jpeg(_) => shape::JpegImage::new_image(AREA.center(), self.image)
                    .with_align(Alignment2D::CENTER)
                    .render(target),
                ImageInfo::Toif(_) => shape::ToifImage::new_image(AREA.center(), self.image)
                    .with_align(Alignment2D::CENTER)
                    .render(target),
                _ => {}
            }

            self.label.map(|t| {
                let r = Rect::new(Point::new(6, 198), Point::new(234, 233));
                shape::Bar::new(r)
                    .with_bg(Color::black())
                    .with_alpha(89)
                    .with_radius(3)
                    .render(target);

                let style = theme::TEXT_DEMIBOLD;
                let pos = Point::new(AREA.center().x, LABEL_Y);
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

                let banner = AREA
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
        sink(AREA);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Homescreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Homescreen");
        t.string("label", self.label);
    }
}

pub struct Lockscreen<'a> {
    label: TString<'a>,
    image: BinaryData<'static>,
    bootscreen: bool,
    coinjoin_authorized: bool,
}

impl<'a> Lockscreen<'a> {
    pub fn new(label: TString<'a>, bootscreen: bool, coinjoin_authorized: bool) -> Self {
        Lockscreen {
            label,
            image: get_homescreen_image(),
            bootscreen,
            coinjoin_authorized,
        }
    }
}

impl Component for Lockscreen<'_> {
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
        todo!()
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let center = AREA.center();

        match ImageInfo::parse(self.image) {
            ImageInfo::Jpeg(_) => shape::JpegImage::new_image(center, self.image)
                .with_align(Alignment2D::CENTER)
                .with_blur(4)
                .with_dim(102)
                .render(target),
            ImageInfo::Toif(_) => shape::ToifImage::new_image(center, self.image)
                .with_align(Alignment2D::CENTER)
                //.with_blur(5)
                .render(target),
            _ => {}
        }

        shape::ToifImage::new(center, ICON_LOCKSCREEN_FILTER.toif)
            .with_align(Alignment2D::CENTER)
            .with_fg(Color::black())
            .render(target);

        shape::ToifImage::new(center + Offset::y(12), ICON_CENTRAL_CIRCLE.toif)
            .with_align(Alignment2D::CENTER)
            .with_fg(GREEN_LIGHT)
            .render(target);

        shape::ToifImage::new(center + Offset::y(12), ICON_KEY.toif)
            .with_align(Alignment2D::CENTER)
            .with_fg(GREY_LIGHT)
            .render(target);

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

        let mut offset = 0;

        self.label.map(|t| {
            offset = theme::TEXT_DEMIBOLD.text_font.visible_text_height(t);

            let text_pos = Point::new(0, offset);

            shape::Text::new(text_pos, t)
                .with_font(theme::TEXT_DEMIBOLD.text_font)
                .with_fg(theme::GREY_LIGHT)
                .render(target);
        });

        offset += 6;

        locked.map_translated(|t| {
            offset += theme::TEXT_SUB_GREY.text_font.visible_text_height(t);

            let text_pos = Point::new(0, offset);

            shape::Text::new(text_pos, t)
                .with_font(theme::TEXT_SUB_GREY.text_font)
                .with_fg(theme::TEXT_SUB_GREY.text_color)
                .render(target);
        });

        tap.map_translated(|t| {
            offset = theme::TEXT_SUB_GREY.text_font.text_baseline();

            let text_pos = Point::new(
                theme::TEXT_SUB_GREY
                    .text_font
                    .horz_center(screen().x0, screen().x1, t),
                screen().y1 - offset,
            );

            shape::Text::new(text_pos, t)
                .with_font(theme::TEXT_SUB_GREY.text_font)
                .with_fg(theme::GREY_DARK)
                .render(target);
        });

        // TODO coinjoin authorized text
    }
}

pub fn check_homescreen_format(image: BinaryData, accept_toif: bool) -> bool {
    match ImageInfo::parse(image) {
        ImageInfo::Jpeg(info) => {
            info.width() == HOMESCREEN_IMAGE_WIDTH
                && info.height() == HOMESCREEN_IMAGE_HEIGHT
                && info.mcu_height() <= 16
        }
        ImageInfo::Toif(info) => {
            accept_toif
                && info.width() == HOMESCREEN_TOIF_SIZE
                && info.height() == HOMESCREEN_TOIF_SIZE
                && info.format() == ToifFormat::FullColorBE
        }
        _ => false,
    }
}

fn get_homescreen_image() -> BinaryData<'static> {
    if let Ok(image) = get_user_custom_image() {
        if check_homescreen_format(image, true) {
            return image;
        }
    }
    IMAGE_HOMESCREEN.into()
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Lockscreen<'_> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Lockscreen");
    }
}
