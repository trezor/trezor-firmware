use crate::{
    io::BinaryData,
    strutil::TString,
    time::{Duration, Instant, Stopwatch},
    translations::TR,
    trezorhal::usb::usb_configured,
    ui::{
        component::{Component, Event, EventCtx, TimerToken},
        display::{image::ImageInfo, toif::Icon, Color, Font},
        event::{TouchEvent, USBEvent},
        geometry::{Alignment, Alignment2D, Offset, Point, Rect},
        layout::util::get_user_custom_image,
        model_mercury::{constant, theme::IMAGE_HOMESCREEN},
        shape::{self, Renderer},
    },
};

use crate::ui::{
    component::Label,
    constant::{screen, HEIGHT, WIDTH},
    model_mercury::{
        cshape,
        theme::{GREY_LIGHT, ICON_KEY, TITLE_HEIGHT},
    },
    shape::{render_on_canvas, ImageBuffer, Rgb565Canvas},
    util::animation_disabled,
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
    label: Label<'static>,
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
            label: Label::new(label, Alignment::Start, theme::TEXT_DEMIBOLD).vertically_centered(),
            notification,
            image: get_homescreen_image(),
            hold_to_lock,
            loader: Loader::with_lock_icon().with_durations(LOADER_DURATION, LOADER_DURATION / 3),
            delay: None,
        }
    }

    fn level_to_style(level: u8) -> (Color, Icon) {
        match level {
            3 => (theme::ORANGE_DARK, theme::ICON_COINJOIN),
            2 => (theme::ORANGE_DARK, theme::ICON_MAGIC),
            1 => (theme::ORANGE_DARK, theme::ICON_WARN),
            _ => (theme::ORANGE_DARK, theme::ICON_WARN),
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
        self.label
            .place(bounds.split_top(TITLE_HEIGHT).0.translate(Offset::x(4)));
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
            if let ImageInfo::Jpeg(_) = ImageInfo::parse(self.image) {
                shape::JpegImage::new_image(AREA.center(), self.image)
                    .with_align(Alignment2D::CENTER)
                    .render(target);
            }

            let label_width = self
                .label
                .text()
                .map(|t| theme::TEXT_DEMIBOLD.text_font.text_width(t));

            let r = Rect::new(Point::new(-30, -30), Point::new(label_width + 12, 42));
            shape::Bar::new(r)
                .with_bg(Color::black())
                .with_alpha(160)
                .with_radius(16)
                .render(target);

            self.label.render(target);

            if let Some(notif) = self.get_notification() {
                const NOTIFICATION_HEIGHT: i16 = 34;
                const NOTIFICATION_TOP: i16 = 202;
                const NOTIFICATION_BORDER: i16 = 16;

                notif.text.map(|t| {
                    let style = theme::TEXT_BOLD;

                    let text_width = style.text_font.text_width(t);

                    let banner = Rect::new(
                        Point::new(
                            AREA.center().x - NOTIFICATION_BORDER - text_width / 2,
                            NOTIFICATION_TOP,
                        ),
                        Point::new(
                            AREA.center().x + NOTIFICATION_BORDER + text_width / 2,
                            NOTIFICATION_TOP + NOTIFICATION_HEIGHT,
                        ),
                    );

                    let text_pos = Point::new(
                        style.text_font.horz_center(banner.x0, banner.x1, t),
                        style.text_font.vert_center(banner.y0, banner.y1, "A"),
                    );

                    shape::Bar::new(banner)
                        .with_radius(16)
                        .with_bg(theme::ORANGE_DARK)
                        .with_alpha(160)
                        .render(target);

                    shape::Text::new(text_pos, t)
                        .with_font(style.text_font)
                        .with_fg(theme::ORANGE_LIGHT)
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
        t.child("label", &self.label);
    }
}

#[derive(Default)]
struct LockscreenAnim {
    pub timer: Stopwatch,
}
impl LockscreenAnim {
    const DURATION_MS: u32 = 1500;

    pub fn is_active(&self) -> bool {
        true
    }

    pub fn eval(&self) -> f32 {
        if animation_disabled() {
            return 0.0;
        }
        let anim = pareen::prop(30.0f32);

        let t: f32 = self.timer.elapsed().to_millis() as f32 / 1000.0;

        anim.eval(t)
    }
}

pub struct Lockscreen {
    anim: LockscreenAnim,
    label: TString<'static>,
    image: BinaryData<'static>,
    bootscreen: bool,
    coinjoin_authorized: bool,
    bg_image: ImageBuffer<Rgb565Canvas<'static>>,
}

impl Lockscreen {
    pub fn new(label: TString<'static>, bootscreen: bool, coinjoin_authorized: bool) -> Self {
        let image = get_homescreen_image();
        let mut buf = unwrap!(ImageBuffer::new(AREA.size()), "no image buf");

        render_on_canvas(buf.canvas(), None, |target| {
            shape::JpegImage::new_image(Point::zero(), image).render(target);
        });

        Lockscreen {
            anim: LockscreenAnim::default(),
            label,
            image,
            bootscreen,
            coinjoin_authorized,
            bg_image: buf,
        }
    }
}

impl Component for Lockscreen {
    type Msg = HomescreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if event == Event::Attach {
            ctx.request_anim_frame();
        }

        if let Event::Timer(EventCtx::ANIM_FRAME_TIMER) = event {
            if (!animation_disabled()) {
                if !self.anim.timer.is_running() {
                    self.anim.timer.start();
                }
                ctx.request_anim_frame();
                ctx.request_paint();
            }
        }

        if let Event::Touch(TouchEvent::TouchEnd(_)) = event {
            return Some(HomescreenMsg::Dismissed);
        }

        None
    }

    fn paint(&mut self) {
        todo!()
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        const OVERLAY_SIZE: i16 = 170;
        const OVERLAY_BORDER: i16 = (AREA.height() - OVERLAY_SIZE) / 2;
        const OVERLAY_OFFSET: i16 = 9;

        let center = AREA.center();

        shape::RawImage::new(AREA, self.bg_image.view()).render(target);

        cshape::UnlockOverlay::new(center + Offset::y(OVERLAY_OFFSET), self.anim.eval())
            .render(target);

        shape::Bar::new(AREA.split_top(OVERLAY_BORDER + OVERLAY_OFFSET).0)
            .with_bg(Color::black())
            .render(target);

        shape::Bar::new(AREA.split_bottom(OVERLAY_BORDER - OVERLAY_OFFSET).1)
            .with_bg(Color::black())
            .render(target);

        shape::Bar::new(AREA.split_left(OVERLAY_BORDER).0)
            .with_bg(Color::black())
            .render(target);

        shape::Bar::new(AREA.split_right(OVERLAY_BORDER).1)
            .with_bg(Color::black())
            .render(target);

        shape::ToifImage::new(center + Offset::y(OVERLAY_OFFSET), ICON_KEY.toif)
            .with_align(Alignment2D::CENTER)
            .with_fg(GREY_LIGHT)
            .render(target);

        let (locked, tap) = if self.bootscreen {
            (
                Some(TR::lockscreen__title_not_connected),
                TR::lockscreen__tap_to_connect,
            )
        } else {
            (None, TR::lockscreen__tap_to_unlock)
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

        if let Some(t) = locked {
            t.map_translated(|t| {
                offset += theme::TEXT_SUB_GREY.text_font.visible_text_height(t);

                let text_pos = Point::new(0, offset);

                shape::Text::new(text_pos, t)
                    .with_font(theme::TEXT_SUB_GREY.text_font)
                    .with_fg(theme::TEXT_SUB_GREY.text_color)
                    .render(target);
            })
        };

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

pub fn check_homescreen_format(image: BinaryData) -> bool {
    match ImageInfo::parse(image) {
        ImageInfo::Jpeg(info) => {
            info.width() == HOMESCREEN_IMAGE_WIDTH
                && info.height() == HOMESCREEN_IMAGE_HEIGHT
                && info.mcu_height() <= 16
        }
        _ => false,
    }
}

fn get_homescreen_image() -> BinaryData<'static> {
    if let Ok(image) = get_user_custom_image() {
        if check_homescreen_format(image) {
            return image;
        }
    }
    IMAGE_HOMESCREEN.into()
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Lockscreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Lockscreen");
    }
}
