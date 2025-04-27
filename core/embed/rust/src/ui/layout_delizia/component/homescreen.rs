#[cfg(feature = "haptic")]
use crate::trezorhal::haptic::{play, HapticEffect};

use crate::{
    error::Error,
    io::BinaryData,
    strutil::TString,
    time::{Duration, Instant, Stopwatch},
    translations::TR,
    trezorhal::usb::usb_configured,
    ui::{
        component::{Component, Event, EventCtx, Timer},
        display::{image::ImageInfo, Color},
        event::TouchEvent,
        geometry::{Alignment, Alignment2D, Insets, Offset, Point, Rect},
        layout::util::get_user_custom_image,
        shape::{self, Renderer},
    },
};

use crate::ui::{
    component::{base::AttachType, Label},
    constant::{screen, HEIGHT, WIDTH},
    lerp::Lerp,
    shape::{render_on_canvas, ImageBuffer, Rgb565Canvas},
    util::animation_disabled,
};

use super::{
    super::{
        cshape::{self, UnlockOverlay},
        fonts,
    },
    constant,
    theme::{self, GREY_LIGHT, HOMESCREEN_ICON, ICON_KEY},
    Loader, LoaderMsg,
};

const AREA: Rect = constant::screen();
const AREA_TAP_TO_UNLOCK: Rect =
    Rect::snap(AREA.center(), Offset::uniform(80), Alignment2D::CENTER);
const TOP_CENTER: Point = AREA.top_center();
const LABEL_Y: i16 = HEIGHT - 18;
const LOCKED_Y: i16 = HEIGHT / 2 - 13;
const TAP_Y: i16 = HEIGHT / 2 + 14;
const HOLD_Y: i16 = 200;
const COINJOIN_Y: i16 = 30;
const LOADER_OFFSET: Offset = Offset::y(-10);
const LOADER_DELAY: Duration = Duration::from_millis(500);
const LOADER_DURATION: Duration = Duration::from_millis(2000);
const LABELS_ALPHA: u8 = 160;

pub const HOMESCREEN_IMAGE_WIDTH: i16 = WIDTH;
pub const HOMESCREEN_IMAGE_HEIGHT: i16 = HEIGHT;

const DEFAULT_HS_RADIUS: i16 = UnlockOverlay::RADIUS;
const DEFAULT_HS_SPAN: i16 = UnlockOverlay::SPAN;
const DEFAULT_HS_THICKNESS: i16 = 6;
const DEFAULT_HS_NUM_CIRCLES: i16 = DEFAULT_HS_COLORS.len() as i16;
#[cfg(any(feature = "universal_fw", feature = "ui_debug"))]
const DEFAULT_HS_COLORS: [Color; 5] = [
    Color::from_u32(0x0BB671),
    Color::from_u32(0x247553),
    Color::from_u32(0x235C44),
    Color::from_u32(0x1D3E30),
    Color::from_u32(0x14271F),
];
#[cfg(not(any(feature = "universal_fw", feature = "ui_debug")))]
const DEFAULT_HS_COLORS: [Color; 5] = [
    Color::from_u32(0xEEA600),
    Color::from_u32(0xB27C00),
    Color::from_u32(0x775300),
    Color::from_u32(0x463100),
    Color::from_u32(0x2C1F00),
];
const DEFAULT_HS_RADII: [i16; 5] = default_hs_radii();
const _: () = debug_assert!(
    DEFAULT_HS_RADII.len() == DEFAULT_HS_COLORS.len(),
    "DEFAULT_HS length mismatch"
);

const NOTIFICATION_HEIGHT: i16 = 30;
const NOTIFICATION_TOP: i16 = 182;
const NOTIFICATION_LOCKSCREEN_TOP: i16 = 190;
const NOTIFICATION_BORDER: i16 = 13;

const NOTIFICATION_BG_ALPHA: u8 = 204;

const NOTIFICATION_BG_RADIUS: i16 = 14;

const fn default_hs_radii() -> [i16; 5] {
    let mut arr = [0i16; 5];
    let mut i = 0;
    while i < DEFAULT_HS_NUM_CIRCLES {
        arr[i as usize] = DEFAULT_HS_RADIUS - DEFAULT_HS_SPAN * i;
        i += 1;
    }
    arr
}

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

        shape::Text::new(text_pos, t, style.text_font)
            .with_fg(notif.color_text)
            .render(target);
    });
}

fn render_instruction<'s>(instruction: TString<'static>, target: &mut impl Renderer<'s>) {
    instruction.map(|t| {
        let offset = theme::TEXT_SUB_GREY.text_font.text_baseline() + theme::SPACING;
        let text_pos = Point::new(
            theme::TEXT_SUB_GREY
                .text_font
                .horz_center(screen().x0, screen().x1, t),
            screen().y1 - offset,
        );
        let rect = Rect::from_bottom_left_and_size(
            screen().bottom_left(),
            Offset::new(screen().width(), 22),
        );

        shape::Bar::new(rect)
            .with_bg(Color::black())
            .with_alpha(LABELS_ALPHA)
            .render(target);
        shape::Text::new(text_pos, t, theme::TEXT_SUB_GREY.text_font)
            .with_fg(theme::GREY_DARK)
            .render(target);
    });
}

fn render_default_hs<'a>(target: &mut impl Renderer<'a>) {
    shape::Bar::new(AREA)
        .with_fg(theme::BG)
        .with_bg(theme::BG)
        .render(target);

    for (rad, color) in DEFAULT_HS_RADII.iter().zip(DEFAULT_HS_COLORS.iter()) {
        shape::Circle::new(AREA.center(), *rad)
            .with_fg(*color)
            .with_bg(theme::BG)
            .with_thickness(DEFAULT_HS_THICKNESS)
            .render(target);
    }

    let innermost_color = unwrap!(DEFAULT_HS_COLORS.last());
    shape::ToifImage::new(AREA.center(), HOMESCREEN_ICON.toif)
        .with_align(Alignment2D::CENTER)
        .with_fg(*innermost_color)
        .render(target);
}

struct HomescreenState {
    attach: AttachAnimationState,
    label: HideLabelAnimationState,
}

static mut HOMESCREEN_STATE: HomescreenState = HomescreenState {
    attach: AttachAnimation::DEFAULT_STATE,
    label: HideLabelAnimation::DEFAULT_STATE,
};

#[derive(Default, Clone)]
struct AttachAnimation {
    pub timer: Stopwatch,
    pub active: bool,
    pub duration: Duration,
    start_opacity: f32,
}

#[derive(Clone, Copy)]
struct AttachAnimationState {
    opacity: u8,
}

impl AttachAnimation {
    const DURATION_MS: u32 = 500;

    pub const DEFAULT_STATE: AttachAnimationState = AttachAnimationState { opacity: 255 };

    fn is_active(&self) -> bool {
        if animation_disabled() {
            return false;
        }

        self.timer.is_running_within(self.duration)
    }

    fn eval(&self) -> f32 {
        if animation_disabled() {
            return 1.0;
        }

        self.timer.elapsed().to_millis() as f32 / 1000.0
    }

    fn opacity(&self, t: f32) -> u8 {
        if animation_disabled() {
            return 255;
        }

        let f = pareen::constant(self.start_opacity)
            .seq_ease_in_out(
                0.0,
                easer::functions::Linear,
                self.duration.to_millis() as f32 / 1000.0,
                pareen::constant(1.0),
            )
            .eval(t);

        (f * 255.0) as u8
    }

    fn start(&mut self) {
        self.active = true;
        self.timer.start();
    }

    fn reset(&mut self) {
        self.active = false;
        self.timer = Stopwatch::new_stopped();
    }

    fn lazy_start(&mut self, ctx: &mut EventCtx, event: Event, resume: AttachAnimationState) {
        match event {
            Event::Attach(AttachType::Initial) => {
                self.duration = Duration::from_millis(Self::DURATION_MS);
                self.reset();
                if !animation_disabled() {
                    ctx.request_anim_frame();
                }
            }
            Event::Attach(AttachType::Resume) => {
                let start_opacity = resume.opacity as f32 / 255.0;
                let duration = start_opacity * Self::DURATION_MS as f32;
                self.start_opacity = start_opacity;
                self.duration = Duration::from_millis(duration as u32);
                self.timer = Stopwatch::new_stopped();
                self.active = resume.opacity < 255;

                if !animation_disabled() {
                    ctx.request_anim_frame();
                }
            }
            Event::Timer(EventCtx::ANIM_FRAME_TIMER) => {
                if !self.timer.is_running() {
                    self.start();
                }
                if self.is_active() {
                    ctx.request_anim_frame();
                    ctx.request_paint();
                } else if self.active {
                    self.active = false;
                    ctx.request_anim_frame();
                    ctx.request_paint();
                }
            }
            _ => {}
        }
    }

    fn get_state(&self, t: f32) -> AttachAnimationState {
        AttachAnimationState {
            opacity: self.opacity(t),
        }
    }
}

struct HideLabelAnimation {
    pub stopwatch: Stopwatch,
    timer: Timer,
    animating: bool,
    hidden: bool,
    duration: Duration,
}

#[derive(Clone, Copy)]
struct HideLabelAnimationState {
    animating: bool,
    hidden: bool,
    elapsed: u32,
}

impl HideLabelAnimation {
    const HIDE_AFTER: Duration = Duration::from_millis(3000);

    pub const DEFAULT_STATE: HideLabelAnimationState = HideLabelAnimationState {
        animating: false,
        hidden: false,
        elapsed: 0,
    };

    fn new(label_width: i16) -> Self {
        Self {
            stopwatch: Stopwatch::default(),
            timer: Timer::new(),
            animating: false,
            hidden: false,
            duration: Duration::from_millis((label_width as u32 * 300) / 120),
        }
    }

    fn is_active(&self) -> bool {
        self.stopwatch.is_running_within(self.duration)
    }

    fn reset(&mut self) {
        self.stopwatch = Stopwatch::default();
    }

    fn elapsed(&self) -> Duration {
        self.stopwatch.elapsed()
    }

    fn change_dir(&mut self) {
        let elapsed = self.stopwatch.elapsed();

        let start = self
            .duration
            .checked_sub(elapsed)
            .and_then(|e| Instant::now().checked_sub(e));

        if let Some(start) = start {
            self.stopwatch = Stopwatch::Running(start);
        } else {
            self.stopwatch = Stopwatch::new_started();
        }
    }

    fn eval(&self, label_width: i16) -> Offset {
        if animation_disabled() {
            return Offset::zero();
        }

        let t = self.stopwatch.elapsed().to_millis() as f32 / 1000.0;

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

    fn eval_for_instruction(&self, text_height: i16) -> Offset {
        if animation_disabled() {
            return Offset::zero();
        }

        let t = self.stopwatch.elapsed().to_millis() as f32 / 1000.0;

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

        Offset::y(i16::lerp(text_height + 12, 0, pos))
    }

    fn process_event(&mut self, ctx: &mut EventCtx, event: Event, resume: HideLabelAnimationState) {
        match event {
            Event::Attach(AttachType::Initial) => {
                ctx.request_anim_frame();
                self.timer.start(ctx, Self::HIDE_AFTER);
            }
            Event::Attach(AttachType::Resume) => {
                self.hidden = resume.hidden;

                let start = Instant::now()
                    .checked_sub(Duration::from_millis(resume.elapsed))
                    .unwrap_or(Instant::now());

                self.animating = resume.animating;

                if self.animating {
                    self.stopwatch = Stopwatch::Running(start);
                    ctx.request_anim_frame();
                } else {
                    self.stopwatch = Stopwatch::new_stopped();
                }
                if !self.animating && !self.hidden {
                    self.timer.start(ctx, Self::HIDE_AFTER);
                }
            }
            Event::Timer(EventCtx::ANIM_FRAME_TIMER) => {
                if self.is_active() {
                    ctx.request_anim_frame();
                    ctx.request_paint();
                } else if self.animating {
                    self.animating = false;
                    self.hidden = !self.hidden;
                    self.reset();
                    ctx.request_paint();

                    if !self.hidden {
                        self.timer.start(ctx, Self::HIDE_AFTER);
                    }
                }
            }
            Event::Timer(_) if self.timer.expire(event) && !animation_disabled() => {
                self.stopwatch.start();
                ctx.request_anim_frame();
                self.animating = true;
                self.hidden = false;
            }

            Event::Touch(TouchEvent::TouchStart(_)) => {
                if !self.animating {
                    if self.hidden {
                        self.stopwatch.start();
                        self.animating = true;
                        ctx.request_anim_frame();
                        ctx.request_paint();
                    } else {
                        self.timer.start(ctx, Self::HIDE_AFTER);
                    }
                } else if !self.hidden {
                    self.change_dir();
                    self.hidden = true;
                    ctx.request_anim_frame();
                    ctx.request_paint();
                }
            }
            _ => {}
        }
    }

    fn get_state(&self) -> HideLabelAnimationState {
        HideLabelAnimationState {
            animating: self.animating,
            hidden: self.hidden,
            elapsed: self.stopwatch.elapsed().to_millis(),
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
    /// Label for the device name, a.k.a "label"
    label_device: Label<'static>,
    /// Label for the "Unlocked" text
    label_unlocked: Label<'static>,
    /// Combined width of both labels
    labels_width: i16,
    /// Combined height of both labels
    labels_height: i16,
    notification: Option<(TString<'static>, u8)>,
    image: Option<BinaryData<'static>>,
    bg_image: ImageBuffer<Rgb565Canvas<'static>>,
    hold_to_lock: bool,
    loader: Loader,
    delay: Timer,
    attach_animation: AttachAnimation,
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
    ) -> Result<Self, Error> {
        let label_width = label.map(|t| theme::TEXT_DEMIBOLD.text_font.text_width(t));
        let label_unlocked = TString::from_translation(TR::words__unlocked);
        let label_unlocked_width =
            label_unlocked.map(|t| theme::TEXT_SUB_GREEN_LIME.text_font.text_width(t));
        let labels_width = label_width.max(label_unlocked_width);

        let label_device_height = theme::TEXT_DEMIBOLD.text_font.text_height();
        let label_unlocked_height = theme::TEXT_SUB_GREEN_LIME.text_font.text_height();
        let labels_height = label_device_height + label_unlocked_height;

        let image = get_homescreen_image();
        let mut buf = ImageBuffer::new(AREA.size())?;

        render_on_canvas(buf.canvas(), None, |target| {
            if let Some(image) = image {
                shape::JpegImage::new_image(Point::zero(), image).render(target);
            } else {
                render_default_hs(target);
            }
        });

        Ok(Self {
            label_device: Label::new(label, Alignment::Start, theme::TEXT_DEMIBOLD)
                .vertically_centered(),
            label_unlocked: Label::new(
                label_unlocked,
                Alignment::Start,
                theme::TEXT_SUB_GREEN_LIME,
            )
            .vertically_centered(),
            labels_width,
            labels_height,
            notification,
            image,
            bg_image: buf,
            hold_to_lock,
            loader: Loader::with_lock_icon().with_durations(LOADER_DURATION, LOADER_DURATION / 3),
            delay: Timer::new(),
            attach_animation: AttachAnimation::default(),
            label_anim: HideLabelAnimation::new(label_width.max(label_unlocked_width)),
        })
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
            shape::Text::new(TOP_CENTER + Offset::y(HOLD_Y), t, fonts::FONT_DEMIBOLD)
                .with_align(Alignment::Center)
                .with_fg(theme::FG);
        });
        self.loader.render(target)
    }

    fn event_usb(&mut self, ctx: &mut EventCtx, event: Event) {
        if let Event::USB(_) = event {
            ctx.request_paint();
        }
    }

    fn event_hold(&mut self, ctx: &mut EventCtx, event: Event) -> bool {
        match event {
            Event::Touch(TouchEvent::TouchStart(_)) => {
                if self.loader.is_animating() {
                    self.loader.start_growing(ctx, Instant::now());
                } else {
                    self.delay.start(ctx, LOADER_DELAY);
                }
            }
            Event::Touch(TouchEvent::TouchEnd(_)) => {
                self.delay.stop();
                let now = Instant::now();
                if self.loader.is_completely_grown(now) {
                    return true;
                }
                if self.loader.is_animating() {
                    self.loader.start_shrinking(ctx, now);
                }
            }
            Event::Timer(_) if self.delay.expire(event) => {
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
        let label_device_height = theme::TEXT_DEMIBOLD.text_font.text_height();
        let label_unlocked_height = theme::TEXT_SUB_GREEN_LIME.text_font.text_height();
        let bounds = bounds.inset(Insets::sides(4));
        let (label_area, rest) = bounds.split_top(label_device_height);
        let (text_unlocked_area, _) = rest.split_top(label_unlocked_height);

        self.label_device
            .place(label_area.with_width(self.labels_width));
        self.label_unlocked
            .place(text_unlocked_area.with_width(self.labels_width));
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // SAFETY: Single threaded access
        let resume_attach = unsafe { HOMESCREEN_STATE.attach };
        self.attach_animation.lazy_start(ctx, event, resume_attach);

        Self::event_usb(self, ctx, event);

        let resume_label = unsafe { HOMESCREEN_STATE.label };

        self.label_anim.process_event(ctx, event, resume_label);

        if self.hold_to_lock {
            Self::event_hold(self, ctx, event).then_some(HomescreenMsg::Dismissed)
        } else {
            None
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if self.loader.is_animating() || self.loader.is_completely_grown(Instant::now()) {
            self.render_loader(target);
        } else {
            let t = self.attach_animation.eval();
            let opacity = self.attach_animation.opacity(t);

            if let Some(image) = self.image {
                if let ImageInfo::Jpeg(_) = ImageInfo::parse(image) {
                    shape::JpegImage::new_image(AREA.center(), image)
                        .with_align(Alignment2D::CENTER)
                        .render(target);
                }
            } else {
                render_default_hs(target);
            }

            let x_offset = self.label_anim.eval(self.labels_width);
            let instruction_text_height = theme::TEXT_SUB_GREY.text_font.text_height();
            let y_offset = self
                .label_anim
                .eval_for_instruction(instruction_text_height);

            target.with_origin(x_offset, &|target| {
                let r = Rect::new(
                    Point::new(-30, -30),
                    Point::new(self.labels_width + 12, self.labels_height + 2),
                );
                shape::Bar::new(r)
                    .with_bg(Color::black())
                    .with_alpha(LABELS_ALPHA)
                    .with_radius(16)
                    .render(target);

                self.label_device.render(target);
                self.label_unlocked.render(target);
            });

            target.with_origin(y_offset, &|target| {
                if let Some(notif) = self.get_notification() {
                    render_notif(notif, NOTIFICATION_TOP, target);
                }
                render_instruction(TR::instructions__continue_in_app.into(), target);
            });

            shape::Bar::new(AREA)
                .with_bg(Color::black())
                .with_alpha(255 - opacity)
                .render(target);

            // SAFETY: Single threaded access
            unsafe {
                HOMESCREEN_STATE.attach = self.attach_animation.get_state(t);
                HOMESCREEN_STATE.label = self.label_anim.get_state();
            }
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Homescreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Homescreen");
        t.child("label", &self.label_device);
    }
}

struct LockscreenState {
    attach: AttachAnimationState,
    overlay: LockscreenAnimState,
    label: HideLabelAnimationState,
}

static mut LOCKSCREEN_STATE: LockscreenState = LockscreenState {
    attach: AttachAnimation::DEFAULT_STATE,
    overlay: LockscreenAnim::DEFAULT_STATE,
    label: HideLabelAnimation::DEFAULT_STATE,
};

#[derive(Default)]
struct LockscreenAnim {
    pub start: f32,
    pub timer: Stopwatch,
}

#[derive(Clone, Copy)]
struct LockscreenAnimState {
    angle: f32,
}

impl LockscreenAnim {
    const DURATION_MS: u32 = 1500;

    pub const DEFAULT_STATE: LockscreenAnimState = LockscreenAnimState { angle: 0.0 };

    pub fn is_active(&self) -> bool {
        true
    }

    pub fn eval(&self) -> f32 {
        if animation_disabled() {
            return 0.0;
        }
        let anim = pareen::prop(30.0f32);

        let t: f32 = self.timer.elapsed().to_millis() as f32 / 1000.0;

        self.start + anim.eval(t)
    }

    pub fn lazy_start(&mut self, ctx: &mut EventCtx, event: Event, resume: LockscreenAnimState) {
        match event {
            Event::Attach(AttachType::Initial) => {
                self.start = 0.0;
                if !animation_disabled() {
                    ctx.request_anim_frame();
                }
            }
            Event::Attach(AttachType::Resume) => {
                self.start = resume.angle;
                if !animation_disabled() {
                    ctx.request_anim_frame();
                }
            }
            Event::Timer(EventCtx::ANIM_FRAME_TIMER) => {
                if !animation_disabled() {
                    if !self.timer.is_running() {
                        self.timer.start();
                    }
                    ctx.request_anim_frame();
                    ctx.request_paint();
                }
            }
            _ => {}
        }
    }

    pub fn get_state(&self) -> LockscreenAnimState {
        LockscreenAnimState { angle: self.eval() }
    }
}

pub struct Lockscreen {
    anim: LockscreenAnim,
    attach_animation: AttachAnimation,
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
    pub fn new(
        label: TString<'static>,
        bootscreen: bool,
        coinjoin_authorized: bool,
    ) -> Result<Self, Error> {
        let image = get_homescreen_image();
        let mut buf = ImageBuffer::new(AREA.size())?;

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

        let label_height = theme::TEXT_DEMIBOLD.text_font.text_height();

        Ok(Self {
            anim: LockscreenAnim::default(),
            attach_animation: AttachAnimation::default(),
            label: Label::new(label, Alignment::Center, theme::TEXT_DEMIBOLD),
            name_width,
            label_width,
            label_height,
            image,
            bootscreen,
            coinjoin_authorized,
            bg_image: buf,
            label_anim: HideLabelAnimation::new(label_width),
        })
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
        // SAFETY: Single threaded access
        let resume_attach = unsafe { LOCKSCREEN_STATE.attach };
        self.attach_animation.lazy_start(ctx, event, resume_attach);

        // SAFETY: Single threaded access
        let resume_overlay = unsafe { LOCKSCREEN_STATE.overlay };
        self.anim.lazy_start(ctx, event, resume_overlay);

        // SAFETY: Single threaded access
        let resume_label = unsafe { LOCKSCREEN_STATE.label };

        let label_hidden = self.label_anim.get_state().hidden;
        let middle = |pos| AREA_TAP_TO_UNLOCK.contains(pos);
        match event {
            // Always dismiss on TouchEnd in the middle area
            Event::Touch(TouchEvent::TouchEnd(pos)) if middle(pos) => {
                #[cfg(feature = "haptic")]
                play(HapticEffect::ButtonPress);
                return Some(HomescreenMsg::Dismissed);
            }
            // Do nothing on TouchStart in the middle area
            Event::Touch(TouchEvent::TouchStart(pos)) if middle(pos) => {}
            // Show label if hidden and tap outside middle area
            Event::Touch(TouchEvent::TouchEnd(pos)) if label_hidden => {
                self.label_anim.process_event(
                    ctx,
                    Event::Touch(TouchEvent::TouchStart(pos)),
                    self.label_anim.get_state(),
                );
                ctx.request_paint();
            }
            // For all other touch events, propagate as usual
            // Ans also for non-touch events
            _ => self.label_anim.process_event(ctx, event, resume_label),
        };
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        const OVERLAY_BORDER: i16 = (AREA.height() / 2) - DEFAULT_HS_RADIUS;

        let center = AREA.center();

        shape::RawImage::new(AREA, self.bg_image.view()).render(target);

        let overlay_rotation = self.anim.eval();
        cshape::UnlockOverlay::new(center, overlay_rotation).render(target);

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

                    shape::Text::new(text_pos, t, theme::TEXT_SUB_GREY.text_font)
                        .with_fg(theme::TEXT_SUB_GREY.text_color)
                        .render(target);
                })
            };
        });

        render_instruction(tap.into(), target);

        if self.coinjoin_authorized {
            let notif = HomescreenNotification {
                text: TR::homescreen__title_coinjoin_authorized.into(),
                color_bg: theme::GREEN_DARK,
                color_text: theme::GREEN_LIME,
            };

            render_notif(notif, NOTIFICATION_LOCKSCREEN_TOP, target);
        }

        let t = self.attach_animation.eval();
        let opacity = self.attach_animation.opacity(t);

        shape::Bar::new(AREA)
            .with_bg(Color::black())
            .with_fg(Color::black())
            .with_alpha(255 - opacity)
            .render(target);

        // SAFETY: Single threaded access
        unsafe {
            LOCKSCREEN_STATE.attach = self.attach_animation.get_state(t);
            LOCKSCREEN_STATE.overlay = self.anim.get_state();
            LOCKSCREEN_STATE.label = self.label_anim.get_state();
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
