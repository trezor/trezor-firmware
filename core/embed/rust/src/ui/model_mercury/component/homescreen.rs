use crate::{
    io::BinaryData,
    strutil::TString,
    time::{Duration, Instant, Stopwatch},
    translations::TR,
    trezorhal::usb::usb_configured,
    ui::{
        component::{Component, Event, EventCtx, TimerToken},
        display::{image::ImageInfo, Color, Font},
        event::{TouchEvent, USBEvent},
        geometry::{Alignment, Alignment2D, Offset, Point, Rect},
        layout::util::get_user_custom_image,
        model_mercury::constant,
        shape::{self, Renderer},
    },
};

use crate::ui::{
    component::Label,
    constant::{screen, HEIGHT, WIDTH},
    lerp::Lerp,
    model_mercury::{
        cshape,
        cshape::UnlockOverlay,
        theme::{GREY_LIGHT, HOMESCREEN_ICON, ICON_KEY},
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

const DEFAULT_HS_RADIUS: i16 = UnlockOverlay::RADIUS;
const DEFAULT_HS_SPAN: i16 = UnlockOverlay::SPAN;
const DEFAULT_HS_THICKNESS: i16 = 6;
const DEFAULT_HS_NUM_CIRCLES: i16 = 5;

const NOTIFICATION_HEIGHT: i16 = 30;
const NOTIFICATION_TOP: i16 = 208;
const NOTIFICATION_LOCKSCREEN_TOP: i16 = 190;
const NOTIFICATION_BORDER: i16 = 13;

const NOTIFICATION_BG_ALPHA: u8 = 204;

const NOTIFICATION_BG_RADIUS: i16 = 14;

fn render_notif<'s>(notif: HomescreenNotification, top: i16, target: &mut impl Renderer<'s>) {
    notif.text.map(|t| {
        let style = theme::TEXT_BOLD;

        let text_width = style.text_font.text_width(t);

        let banner = Rect::new(
            Point::new(AREA.center().x - NOTIFICATION_BORDER - text_width / 2, top),
            Point::new(
                AREA.center().x + NOTIFICATION_BORDER + text_width / 2,
                top + NOTIFICATION_HEIGHT,
            ),
        );

        let text_pos = Point::new(
            style.text_font.horz_center(banner.x0, banner.x1, t),
            style.text_font.vert_center(banner.y0, banner.y1, "A"),
        );

        shape::Bar::new(banner)
            .with_radius(NOTIFICATION_BG_RADIUS)
            .with_bg(notif.color_bg)
            .with_alpha(NOTIFICATION_BG_ALPHA)
            .render(target);

        shape::Text::new(text_pos, t)
            .with_font(style.text_font)
            .with_fg(notif.color_text)
            .render(target);
    });
}

fn render_default_hs<'a>(target: &mut impl Renderer<'a>) {
    shape::Bar::new(AREA)
        .with_fg(theme::BG)
        .with_bg(theme::BG)
        .render(target);

    #[cfg(any(feature = "universal_fw", feature = "ui_debug"))]
    let colors = [0x0BB671, 0x247553, 0x235C44, 0x1D3E30, 0x14271F];
    #[cfg(not(any(feature = "universal_fw", feature = "ui_debug")))]
    let colors = [0xEEA600, 0xB27C00, 0x775300, 0x463100, 0x2C1F00];

    for i in 0..DEFAULT_HS_NUM_CIRCLES {
        let r = DEFAULT_HS_RADIUS - i * DEFAULT_HS_SPAN;
        let fg = Color::from_u32(colors[i as usize]);
        let bg = theme::BG;
        let thickness = DEFAULT_HS_THICKNESS;
        shape::Circle::new(AREA.center(), r)
            .with_fg(fg)
            .with_bg(bg)
            .with_thickness(thickness)
            .render(target);
    }

    shape::ToifImage::new(AREA.center(), HOMESCREEN_ICON.toif)
        .with_align(Alignment2D::CENTER)
        .render(target);
}

struct HideLabelAnimation {
    pub timer: Stopwatch,
    token: TimerToken,
    animating: bool,
    hidden: bool,
    duration: Duration,
}
impl HideLabelAnimation {
    const HIDE_AFTER: Duration = Duration::from_millis(3000);

    fn new(label_width: i16) -> Self {
        Self {
            timer: Stopwatch::default(),
            token: TimerToken::INVALID,
            animating: false,
            hidden: false,
            duration: Duration::from_millis((label_width as u32 * 300) / 120),
        }
    }

    fn is_active(&self) -> bool {
        self.timer.is_running_within(self.duration)
    }

    fn reset(&mut self) {
        self.timer = Stopwatch::default();
    }

    fn change_dir(&mut self) {
        let elapsed = self.timer.elapsed();

        let start = self
            .duration
            .checked_sub(elapsed)
            .and_then(|e| Instant::now().checked_sub(e));

        if let Some(start) = start {
            self.timer = Stopwatch::Running(start);
        } else {
            self.timer = Stopwatch::new_started();
        }
    }

    fn eval(&self, label_width: i16) -> Offset {
        if animation_disabled() {
            return Offset::zero();
        }

        let t = self.timer.elapsed().to_millis() as f32 / 1000.0;

        let pos = if self.hidden {
            pareen::constant(0.0)
                .seq_ease_out(
                    0.0,
                    easer::functions::Cubic,
                    self.duration.to_millis() as f32 / 1000.0,
                    pareen::constant(1.0),
                )
                .eval(t)
        } else {
            pareen::constant(1.0)
                .seq_ease_in(
                    0.0,
                    easer::functions::Cubic,
                    self.duration.to_millis() as f32 / 1000.0,
                    pareen::constant(0.0),
                )
                .eval(t)
        };

        Offset::x(i16::lerp(-(label_width + 12), 0, pos))
    }

    fn process_event(&mut self, ctx: &mut EventCtx, event: Event) {
        if let Event::Attach(_) = event {
            ctx.request_anim_frame();
            self.token = ctx.request_timer(Self::HIDE_AFTER);
        }

        if let Event::Timer(token) = event {
            if token == self.token && !animation_disabled() {
                self.timer.start();
                ctx.request_anim_frame();
                self.animating = true;
                self.hidden = false;
            }
        }

        if let Event::Timer(EventCtx::ANIM_FRAME_TIMER) = event {
            if self.is_active() {
                ctx.request_anim_frame();
                ctx.request_paint();
            } else if self.animating {
                self.animating = false;
                self.hidden = !self.hidden;
                self.reset();
                ctx.request_paint();

                if !self.hidden {
                    self.token = ctx.request_timer(Self::HIDE_AFTER);
                }
            }
        }

        if let Event::Touch(TouchEvent::TouchStart(_)) = event {
            if !self.animating {
                if self.hidden {
                    self.timer.start();
                    self.animating = true;
                    ctx.request_anim_frame();
                    ctx.request_paint();
                } else {
                    self.token = ctx.request_timer(Self::HIDE_AFTER);
                }
            } else if !self.hidden {
                self.change_dir();
                self.hidden = true;
                ctx.request_anim_frame();
                ctx.request_paint();
            }
        }
    }
}

#[derive(Clone, Copy)]
pub struct HomescreenNotification {
    pub text: TString<'static>,
    pub color_bg: Color,
    pub color_text: Color,
}

pub struct Homescreen {
    label: Label<'static>,
    label_width: i16,
    label_height: i16,
    notification: Option<(TString<'static>, u8)>,
    image: Option<BinaryData<'static>>,
    bg_image: ImageBuffer<Rgb565Canvas<'static>>,
    hold_to_lock: bool,
    loader: Loader,
    delay: Option<TimerToken>,
    label_anim: HideLabelAnimation,
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
        let label_width = label.map(|t| theme::TEXT_DEMIBOLD.text_font.text_width(t));
        let label_height = label.map(|t| theme::TEXT_DEMIBOLD.text_font.visible_text_height(t));

        let image = get_homescreen_image();
        let mut buf = unwrap!(ImageBuffer::new(AREA.size()), "no image buf");

        render_on_canvas(buf.canvas(), None, |target| {
            if let Some(image) = image {
                shape::JpegImage::new_image(Point::zero(), image).render(target);
            } else {
                render_default_hs(target);
            }
        });

        Self {
            label: Label::new(label, Alignment::Center, theme::TEXT_DEMIBOLD).vertically_centered(),
            label_width,
            label_height,
            notification,
            image,
            bg_image: buf,
            hold_to_lock,
            loader: Loader::with_lock_icon().with_durations(LOADER_DURATION, LOADER_DURATION / 3),
            delay: None,
            label_anim: HideLabelAnimation::new(label_width),
        }
    }

    fn level_to_style(level: u8) -> (Color, Color) {
        match level {
            3 => (theme::GREEN_DARK, theme::GREEN_LIME),
            _ => (theme::ORANGE_DARK, theme::ORANGE_LIGHT),
        }
    }

    fn get_notification(&self) -> Option<HomescreenNotification> {
        if !usb_configured() {
            let (color_bg, color_text) = Self::level_to_style(0);
            Some(HomescreenNotification {
                text: TR::homescreen__title_no_usb_connection.into(),
                color_bg,
                color_text,
            })
        } else if let Some((notification, level)) = self.notification {
            let (color_bg, color_text) = Self::level_to_style(level);
            Some(HomescreenNotification {
                text: notification,
                color_bg,
                color_text,
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
            .place(bounds.split_top(32).0.with_width(self.label_width + 12));
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        Self::event_usb(self, ctx, event);

        self.label_anim.process_event(ctx, event);

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
            shape::RawImage::new(AREA, self.bg_image.view()).render(target);

            let y_offset = self.label_anim.eval(self.label_width);

            target.with_origin(y_offset, &|target| {
                let label_width = self
                    .label
                    .text()
                    .map(|t| theme::TEXT_DEMIBOLD.text_font.text_width(t));

                let r = Rect::new(Point::new(-30, -30), Point::new(label_width + 12, 32));
                shape::Bar::new(r)
                    .with_bg(Color::black())
                    .with_alpha(160)
                    .with_radius(16)
                    .render(target);

                self.label.render(target);
            });

            if let Some(notif) = self.get_notification() {
                render_notif(notif, NOTIFICATION_TOP, target);
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
    label: Label<'static>,
    name_width: i16,
    label_width: i16,
    label_height: i16,
    image: Option<BinaryData<'static>>,
    bootscreen: bool,
    coinjoin_authorized: bool,
    bg_image: ImageBuffer<Rgb565Canvas<'static>>,
    label_anim: HideLabelAnimation,
}

impl Lockscreen {
    pub fn new(label: TString<'static>, bootscreen: bool, coinjoin_authorized: bool) -> Self {
        let image = get_homescreen_image();
        let mut buf = unwrap!(ImageBuffer::new(AREA.size()), "no image buf");

        render_on_canvas(buf.canvas(), None, |target| {
            if let Some(image) = image {
                shape::JpegImage::new_image(Point::zero(), image).render(target);
            } else {
                render_default_hs(target);
            }
        });

        let name_width = label.map(|t| theme::TEXT_DEMIBOLD.text_font.text_width(t));

        let label_width = if bootscreen {
            let min = TR::lockscreen__title_not_connected
                .map_translated(|t| theme::TEXT_SUB_GREY.text_font.text_width(t));
            name_width.max(min)
        } else {
            name_width
        };

        let label_height = label.map(|t| theme::TEXT_DEMIBOLD.text_font.visible_text_height(t));

        Lockscreen {
            anim: LockscreenAnim::default(),
            label: Label::new(label, Alignment::Center, theme::TEXT_DEMIBOLD),
            name_width,
            label_width,
            label_height,
            image,
            bootscreen,
            coinjoin_authorized,
            bg_image: buf,
            label_anim: HideLabelAnimation::new(label_width),
        }
    }
}

impl Component for Lockscreen {
    type Msg = HomescreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.label
            .place(bounds.split_top(38).0.with_width(self.name_width + 12));
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Event::Attach(_) = event {
            ctx.request_anim_frame();
        }

        if let Event::Timer(EventCtx::ANIM_FRAME_TIMER) = event {
            if !animation_disabled() {
                if !self.anim.timer.is_running() {
                    self.anim.timer.start();
                }
                ctx.request_anim_frame();
                ctx.request_paint();
            }
        }

        self.label_anim.process_event(ctx, event);

        if let Event::Touch(TouchEvent::TouchEnd(_)) = event {
            return Some(HomescreenMsg::Dismissed);
        }

        None
    }

    fn paint(&mut self) {
        todo!()
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        const OVERLAY_BORDER: i16 = (AREA.height() / 2) - DEFAULT_HS_RADIUS;

        let center = AREA.center();

        shape::RawImage::new(AREA, self.bg_image.view()).render(target);

        cshape::UnlockOverlay::new(center, self.anim.eval()).render(target);

        shape::Bar::new(AREA.split_top(OVERLAY_BORDER).0)
            .with_bg(Color::black())
            .render(target);

        shape::Bar::new(AREA.split_bottom(OVERLAY_BORDER - 2).1)
            .with_bg(Color::black())
            .render(target);

        shape::Bar::new(AREA.split_left(OVERLAY_BORDER).0)
            .with_bg(Color::black())
            .render(target);

        shape::Bar::new(AREA.split_right(OVERLAY_BORDER - 2).1)
            .with_bg(Color::black())
            .render(target);

        shape::ToifImage::new(center, ICON_KEY.toif)
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

        let y_offset = self.label_anim.eval(self.label_width);

        let mut offset = 6 + self.label_height;

        if let Some(t) = locked {
            t.map_translated(|t| {
                offset += theme::TEXT_SUB_GREY.text_font.visible_text_height(t);
            });
        }

        target.with_origin(y_offset, &|target| {
            self.label.render(target);

            if let Some(t) = locked {
                t.map_translated(|t| {
                    let text_pos = Point::new(6, offset);

                    shape::Text::new(text_pos, t)
                        .with_font(theme::TEXT_SUB_GREY.text_font)
                        .with_fg(theme::TEXT_SUB_GREY.text_color)
                        .render(target);
                })
            };
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

        if self.coinjoin_authorized {
            let notif = HomescreenNotification {
                text: TR::homescreen__title_coinjoin_authorized.into(),
                color_bg: theme::GREEN_DARK,
                color_text: theme::GREEN_LIME,
            };

            render_notif(notif, NOTIFICATION_LOCKSCREEN_TOP, target);
        }
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

fn get_homescreen_image() -> Option<BinaryData<'static>> {
    if let Ok(image) = get_user_custom_image() {
        if check_homescreen_format(image) {
            return Some(image);
        }
    }
    None
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Lockscreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Lockscreen");
    }
}
