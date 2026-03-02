use crate::{
    error::Error,
    io::BinaryData,
    strutil::TString,
    time::{Duration, Instant, Stopwatch},
    translations::TR,
    ui::{
        component::{Component, Event, EventCtx, Label, Never, Swipe, Timer},
        display::{image::ImageInfo, Color},
        event::TouchEvent,
        geometry::{Alignment2D, Direction, Insets, Offset, Point, Rect},
        layout::util::get_user_custom_image,
        lerp::Lerp,
        notification::{Notification, NotificationLevel},
        shape::{self, Renderer},
        util::animation_disabled,
    },
};

use super::{
    super::component::{Button, ButtonContent, ConnectionIndicator, FuelGauge},
    constant::{HEIGHT, SCREEN, WIDTH},
    theme::{self, firmware::button_homebar_style, ScreenBackground},
    ActionBar, ActionBarMsg, Hint,
};

#[cfg(feature = "rgb_led")]
use crate::ui::led::LedState;

/// Full-screen component for the homescreen and lockscreen.
pub struct Homescreen {
    /// Device name label, fuel gauge, and connection status
    status: HomescreenStatus,
    /// Notification
    hint: Option<Hint<'static>>,
    /// Home action bar
    action_bar: ActionBar,
    /// Background image
    image: Option<BinaryData<'static>>,
    /// LED color
    led_color: Option<Color>,
    /// Whether the homescreen is locked
    locked: bool,
    /// Whether the homescreen is a boot screen
    bootscreen: bool,
    /// Swipe component for vertical swiping
    swipe: Swipe,
    // swipe_config: SwipeConfig,
}

pub enum HomescreenMsg {
    Dismissed,
    Menu,
}

impl Homescreen {
    pub fn new(
        label: TString<'static>,
        _lockable: bool,
        locked: bool,
        bootscreen: bool,
        coinjoin_authorized: bool,
        notification: Option<Notification>,
    ) -> Result<Self, Error> {
        let image = get_homescreen_image();

        // Notification
        let (led_color, hint) = match notification {
            Some(ref notification) => {
                let (led_color, hint) = Self::get_notification_display(notification);
                (Some(led_color), Some(hint))
            }
            None if locked && coinjoin_authorized => (
                Some(theme::LED_GREEN_LIME),
                Some(Hint::new_instruction_green(
                    TR::coinjoin__do_not_disconnect,
                    Some(theme::ICON_INFO),
                )),
            ),
            None => (None, None),
        };

        // Homebar
        let (style_sheet, gradient) = button_homebar_style(notification.map(|n| n.level));
        let btn = Button::new(Self::homebar_content(bootscreen, locked))
            .styled(style_sheet)
            .with_gradient(gradient);

        Ok(Self {
            status: HomescreenStatus::new(label.clone(), image.is_some()),
            hint,
            action_bar: ActionBar::new_single(btn),
            image,
            led_color,
            locked,
            bootscreen,
            swipe: Swipe::new().up(),
        })
    }

    fn homebar_content(bootscreen: bool, locked: bool) -> ButtonContent {
        let text = (bootscreen || locked).then_some(TR::lockscreen__unlock.into());
        ButtonContent::HomeBar(text)
    }

    fn get_notification_display(n: &Notification) -> (Color, Hint<'static>) {
        match n.level {
            NotificationLevel::Alert => (theme::LED_RED, Hint::new_warning_danger(n.text)),
            NotificationLevel::Warning => (theme::LED_YELLOW, Hint::new_warning_neutral(n.text)),
            NotificationLevel::Info => (theme::LED_BLUE, Hint::new_instruction(n.text, None)),
            NotificationLevel::Success => (
                theme::LED_GREEN_LIGHT,
                Hint::new_instruction_green(n.text, Some(theme::ICON_INFO)),
            ),
        }
    }
}

impl Component for Homescreen {
    type Msg = HomescreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        let (rest, bar_area) = bounds.split_bottom(theme::ACTION_BAR_HEIGHT);
        let status_area = if let Some(hint) = &mut self.hint {
            let (rest, hint_area) = rest.split_bottom(hint.height());
            hint.place(hint_area);
            rest
        } else {
            rest
        };

        self.status.place(status_area.inset(theme::SIDE_INSETS));
        self.action_bar.place(bar_area);
        // Swipe component is placed in the action bar touch area
        self.swipe.place(self.action_bar.touch_area());
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.status.event(ctx, event);
        let swipe_up = matches!(self.swipe.event(ctx, event), Some(Direction::Up));
        let homebar_tap = matches!(
            self.action_bar.event(ctx, event),
            Some(ActionBarMsg::Confirmed)
        );
        if swipe_up || homebar_tap {
            return if self.locked {
                Some(HomescreenMsg::Dismissed)
            } else {
                Some(HomescreenMsg::Menu)
            };
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if let Some(image) = self.image {
            if let ImageInfo::Jpeg(_) = ImageInfo::parse(image) {
                shape::JpegImage::new_image(SCREEN.top_left(), image).render(target);
            }
        } else {
            ScreenBackground::new(self.led_color, None).render(target);
        }
        self.status.render(target);
        self.hint.render(target);
        self.action_bar.render(target);

        #[cfg(feature = "rgb_led")]
        target.set_led_state(LedState::Static(
            self.led_color.unwrap_or_else(Color::black),
        ));
    }
}

/// Helper component that displays device name label, battery status, and
/// connection status indicator.
/// It is combined because the label is shown together with the fuel gauge and
/// connection indicator when a custom background image is used.
struct HomescreenStatus {
    area: Rect,
    /// Device name
    label: Label<'static>,
    /// Fuel gauge (battery status indicator)
    fuel_gauge: FuelGauge,
    /// Whether the device is connected to Host (either via USB or BLE)
    connection_indicator: ConnectionIndicator,
    /// Whether a custom background image is used, which affects the layout and
    /// styling of the label
    background_image: bool,
    /// Cached text width of the label when a custom background image is used
    text_width: Option<i16>,
    /// Animation for hiding/showing the label when background_image is true
    label_anim: Option<HideLabelAnimation>,
    /// Cached pill-shaped background area (used when background_image is true)
    shadow_area: Rect,
    /// Cached label clipping window (used when background_image is true)
    label_area: Rect,
}

impl HomescreenStatus {
    pub const SUBCOMPONENTS_GAP: i16 = 16;
    const SHADOW_HEIGHT: i16 = 54;
    const SHADOW_OFFSET_X: Offset = Offset::x(Self::SHADOW_HEIGHT / 2);
    const SHADOW_ANCHOR: Point = Point::new(0, 21).ofs(Self::SHADOW_OFFSET_X.neg());

    pub fn new(label: TString<'static>, background_image: bool) -> Self {
        let (style, text_width, label_animation) = if background_image {
            let style = theme::firmware::TEXT_SMALL;
            let width = label.map(|text| style.text_font.text_width(text));
            (style, Some(width), Some(HideLabelAnimation::new(width)))
        } else {
            (theme::firmware::TEXT_BIG, None, None)
        };

        Self {
            area: Rect::zero(),
            label: Label::left_aligned(label, style).top_aligned(),
            fuel_gauge: FuelGauge::always_icon_only(),
            connection_indicator: ConnectionIndicator::new(),
            background_image,
            text_width,
            label_anim: label_animation,
            shadow_area: Rect::zero(),
            label_area: Rect::zero(),
        }
    }

    fn render_pill_shaped_background<'s>(&'s self, area: Rect, target: &mut impl Renderer<'s>) {
        const SHADOW_ALPHA: u8 = 230; // 90%
        shape::Bar::new(area)
            .with_bg(theme::BG)
            .with_fg(theme::BG)
            .with_radius(Self::SHADOW_HEIGHT / 2)
            .with_alpha(SHADOW_ALPHA)
            .render(target);
    }
}

impl Component for HomescreenStatus {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        const LABEL_INSETS_DEFAULT: Insets = Insets::new(83, 24, 24, 0);

        let (header_area, _) = bounds.split_top(theme::HEADER_HEIGHT);
        let (fuel_gauge_area, _) = header_area.split_left(self.fuel_gauge.content_width());
        let connection_indicator_area = Rect::snap(
            fuel_gauge_area.right_center(),
            Offset::uniform(ConnectionIndicator::AREA_SIZE_NEEDED),
            Alignment2D::CENTER_LEFT,
        )
        .translate(Offset::x(Self::SUBCOMPONENTS_GAP));

        self.fuel_gauge.place(fuel_gauge_area);
        self.connection_indicator.place(connection_indicator_area);

        let label_area = if !self.background_image {
            bounds.inset(LABEL_INSETS_DEFAULT)
        } else {
            let anchor = if self.connection_indicator.connected {
                connection_indicator_area.right_center()
            } else {
                fuel_gauge_area.right_center()
            };
            Rect::snap(
                anchor,
                Offset::new(self.text_width.unwrap_or(0), self.label.font().max_height),
                Alignment2D::CENTER_LEFT,
            )
            .translate(Offset::x(Self::SUBCOMPONENTS_GAP))
        };
        self.label.place(label_area);

        if self.background_image {
            self.label_area = label_area;
            // pill background spans from off-screen left to cover the full status row
            let shadow_size =
                Offset::new(label_area.x1, Self::SHADOW_HEIGHT) + Self::SHADOW_OFFSET_X * 2.0;
            self.shadow_area = Rect::from_top_left_and_size(Self::SHADOW_ANCHOR, shadow_size);
        }

        self.area = bounds;
        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.fuel_gauge.event(ctx, event);
        let connection_event = self.connection_indicator.event(ctx, event);
        if matches!(event, Event::PM(_)) || connection_event.is_some() {
            // TODO: could FuelGauge also return Some(()) on update?
            self.place(self.area);
            ctx.request_paint();
        }

        if let Some(label_anim) = &mut self.label_anim {
            label_anim.process_event(ctx, event);
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if self.background_image {
            if let Some(animation) = &self.label_anim {
                let x_offset = animation.eval_offset();
                target.with_origin(x_offset, &|target| {
                    self.render_pill_shaped_background(self.shadow_area, target);
                });
                target.in_clip(self.label_area, &|target| {
                    target.with_origin(x_offset, &|target| {
                        self.label.render(target);
                    });
                });
            }
        } else {
            self.label.render(target);
        }
        self.fuel_gauge.render(target);
        self.connection_indicator.render(target);
    }
}

struct HideLabelAnimation {
    pub stopwatch: Stopwatch,
    pub timer: Timer,
    pub duration: Duration,
    label_width: i16,
    animating: bool,
    hidden: bool,
}

impl HideLabelAnimation {
    const HIDE_AFTER: Duration = Duration::from_millis(3000);
    const MOVE_DURATION: Duration = Duration::from_millis(500);

    pub fn new(label_width: i16) -> Self {
        Self {
            stopwatch: Stopwatch::default(),
            timer: Timer::new(),
            duration: Duration::from_millis((label_width as u32 * 300) / 120),
            label_width,
            animating: false,
            hidden: false,
        }
    }

    fn is_active(&self) -> bool {
        self.stopwatch.is_running_within(self.duration)
    }

    fn reset(&mut self) {
        self.stopwatch = Stopwatch::default();
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

    fn eval(&self) -> f32 {
        if animation_disabled() {
            return 1.0;
        }

        let t = self.stopwatch.elapsed().to_millis() as f32 / 1000.0;

        if self.hidden {
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
        }
    }

    pub fn eval_offset(&self) -> Offset {
        if animation_disabled() {
            return Offset::zero();
        }

        let pos = self.eval();
        Offset::x(i16::lerp(
            -(self.label_width + HomescreenStatus::SUBCOMPONENTS_GAP),
            0,
            pos,
        ))
    }

    pub fn process_event(&mut self, ctx: &mut EventCtx, event: Event) {
        match event {
            Event::Attach(_) => {
                self.timer.start(ctx, Self::HIDE_AFTER);
                ctx.request_anim_frame();
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
            Event::Touch(TouchEvent::TouchStart(point)) => {
                // Only trigger animation at the top of the screen
                if point.y <= SCREEN.height() / 2 {
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
            }
            _ => {}
        }
    }
}

pub fn check_homescreen_format(image: BinaryData) -> bool {
    match ImageInfo::parse(image) {
        ImageInfo::Jpeg(info) => {
            info.width() == WIDTH && info.height() == HEIGHT && info.mcu_height() <= 16
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
impl crate::trace::Trace for Homescreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Homescreen");
        t.child("status", &self.status);
        t.child("homebar", &self.action_bar);
    }
}
#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for HomescreenStatus {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("HomescreenStatus");
        t.child("label", &self.label);
        t.child("fuel_gauge", &self.fuel_gauge);
        t.child("connection_indicator", &self.connection_indicator);
    }
}
