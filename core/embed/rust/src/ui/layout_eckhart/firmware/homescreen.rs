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
        geometry::{Alignment2D, Direction, Offset, Point, Rect},
        layout::util::get_user_custom_image,
        lerp::Lerp,
        notification::{Notification, NotificationLevel},
        shape::{self, Renderer},
        util::animation_disabled,
    },
};
use core::sync::atomic::{AtomicBool, Ordering};

use super::{
    super::component::{Button, ButtonContent, ConnectionIndicator, FuelGauge},
    constant::{HEIGHT, SCREEN, WIDTH},
    theme::{self, firmware::button_homebar_style, ScreenBackground},
    ActionBar, ActionBarMsg, Hint,
};

#[cfg(feature = "rgb_led")]
use crate::ui::led::LedState;

const SHADOW_HEIGHT: i16 = 54;

/// Full-screen component for the homescreen and lockscreen.
pub struct Homescreen {
    /// Device name label, fuel gauge, and connection status
    header: HomescreenHeader,
    /// Notification rendering, including LED and hint text
    notification_center: HomescreenNotificationCenter,
    /// Home action bar
    action_bar: ActionBar,
    /// Background image
    image: Option<BinaryData<'static>>,
    /// Whether the homescreen is locked
    locked: bool,
    /// Whether the homescreen is a boot screen
    bootscreen: bool,
    /// Swipe component for vertical swiping
    swipe: Swipe,
    /// Notification homebar button (with notification style), if applicable
    notification_btn: Option<Button>,
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
        let image_used = image.is_some();

        let notification_center = HomescreenNotificationCenter::new(
            notification,
            locked,
            coinjoin_authorized,
            image_used,
        );

        // Build the default homebar (as if no notification)
        let default_btn = Self::make_default_homebar(bootscreen, locked);
        // Build the notification homebar if there's an actionable notification
        let notification_btn = if notification_center.actionable_notification {
            Some(notification_center.homebar_button(bootscreen, locked))
        } else {
            None
        };

        let is_alert = notification_center.is_alert();
        let show_immediately = is_alert || animation_disabled();

        // Start with default button unless notification shows immediately
        let initial_btn = if show_immediately && notification_btn.is_some() {
            notification_center.homebar_button(bootscreen, locked)
        } else {
            default_btn
        };

        Ok(Self {
            header: HomescreenHeader::new(label, image_used, !is_alert),
            notification_center,
            action_bar: ActionBar::new_single(initial_btn),
            image,
            locked,
            bootscreen,
            swipe: Swipe::new().up(),
            notification_btn,
        })
    }

    /// Build a homebar button with default style (no notification)
    fn make_default_homebar(bootscreen: bool, locked: bool) -> Button {
        let text: Option<TString<'static>> = if bootscreen || locked {
            Some(TR::lockscreen__unlock.into())
        } else {
            None
        };
        let (style_sheet, gradient) = button_homebar_style(None, false);
        Button::new(ButtonContent::HomeBar(text))
            .styled(style_sheet)
            .with_gradient(gradient)
    }
}

impl Component for Homescreen {
    type Msg = HomescreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        let (rest, bar_area) = bounds.split_bottom(theme::ACTION_BAR_HEIGHT);
        let (status_area, rest) = rest.split_top(theme::HEADER_HEIGHT);

        self.header.place(status_area.inset(theme::SIDE_INSETS));
        self.notification_center.place(rest);
        self.action_bar.place(bar_area);
        // Swipe component is placed in the action bar touch area
        self.swipe.place(self.action_bar.touch_area());
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.header.event(ctx, event);
        self.notification_center.event(ctx, event);

        // Swap action bar to notification style when notification becomes visible
        if self.notification_center.notification_visible {
            if let Some(btn) = self.notification_btn.take() {
                self.action_bar = ActionBar::new_single(btn);
                // Re-place the action bar in its area
                let bar_area = SCREEN.split_bottom(theme::ACTION_BAR_HEIGHT).1;
                self.action_bar.place(bar_area);
                self.swipe.place(self.action_bar.touch_area());
                ctx.request_paint();
            }
        }

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
        }
        self.notification_center.render(target);
        self.header.render(target);
        self.action_bar.render(target);
    }
}

struct HomescreenNotificationCenter {
    /// Current notification to display, if any
    notification: Option<Notification>,
    /// Whether the notification is actionable (i.e. has a corresponding entry
    /// in the DeviceMenu)
    actionable_notification: bool,
    /// Notification text display
    hint: Option<Hint<'static>>,
    hint_shadow_area: Rect,
    /// LED color
    led_color: Option<Color>,
    /// Whether the LED is currently active
    led_active: bool,
    /// Timer for toggling the LED on/off
    led_timer: Timer,
    /// Whether a custom background image is used, which affects the UI
    background_image: bool,
    /// Whether the notification UI (hint/actionbar) has become visible.
    /// Starts false, becomes true after the first LED toggle duration,
    /// and stays true permanently.
    notification_visible: bool,
}

impl HomescreenNotificationCenter {
    pub fn new(
        notification: Option<Notification>,
        locked: bool,
        coinjoin_authorized: bool,
        background_image: bool,
    ) -> Self {
        // If there's a notification which has an entry in the DeviceMenu
        let actionable_notification = notification.as_ref().is_some_and(|n| n.actionable);

        let led_color = match notification {
            Some(ref notification) => Some(Self::get_notification_led_color(notification)),
            None if locked && coinjoin_authorized => Some(theme::LED_GREEN_LIME),
            None => None,
        };

        let hint = match notification {
            Some(ref n) if !n.actionable => Some(Self::get_notification_hint(n)),
            None if locked && coinjoin_authorized => Some(Hint::new_instruction_green(
                TR::coinjoin__do_not_disconnect,
                Some(theme::ICON_INFO),
            )),
            _ => None,
        };

        // Alerts are visible immediately
        let is_alert = notification
            .as_ref()
            .map(|n| matches!(n.level, NotificationLevel::Alert))
            .unwrap_or(false);
        let show_immediately = is_alert || animation_disabled();

        Self {
            notification,
            actionable_notification,
            hint,
            hint_shadow_area: Rect::zero(),
            led_color,
            led_active: false,
            led_timer: Timer::new(),
            background_image,
            notification_visible: show_immediately && led_color.is_some(),
        }
    }

    pub fn homebar_button(&self, bootscreen: bool, locked: bool) -> Button {
        let text: Option<TString<'static>> = if bootscreen || locked {
            Some(TR::lockscreen__unlock.into())
        } else if self.actionable_notification {
            self.notification.as_ref().map(|n| n.text)
        } else {
            None
        };
        let level = self.notification.as_ref().map(|n| n.level);
        let (style_sheet, gradient) =
            button_homebar_style(level.as_ref(), self.actionable_notification);
        Button::new(ButtonContent::HomeBar(text))
            .styled(style_sheet)
            .with_gradient(gradient)
    }

    fn notification_level(&self) -> Option<NotificationLevel> {
        self.notification.as_ref().map(|n| n.level)
    }

    fn is_alert(&self) -> bool {
        self.notification_level()
            .map(|level| matches!(level, NotificationLevel::Alert))
            .unwrap_or(false)
    }

    fn get_notification_led_color(n: &Notification) -> Color {
        match n.level {
            NotificationLevel::Alert => theme::LED_RED,
            NotificationLevel::Warning => theme::LED_YELLOW,
            NotificationLevel::Info => theme::LED_BLUE,
            NotificationLevel::Success => theme::LED_GREEN_LIGHT,
        }
    }

    fn get_notification_hint(n: &Notification) -> Hint<'static> {
        match n.level {
            NotificationLevel::Alert => Hint::new_warning_danger(n.text),
            NotificationLevel::Warning => Hint::new_warning_neutral(n.text),
            NotificationLevel::Info => Hint::new_instruction(n.text, None),
            NotificationLevel::Success => {
                Hint::new_instruction_green(n.text, Some(theme::ICON_INFO))
            }
        }
    }
}

impl Component for HomescreenNotificationCenter {
    type Msg = Never;
    fn place(&mut self, bounds: Rect) -> Rect {
        if let Some(hint) = &mut self.hint {
            let hint_height = hint.height();
            let hint_height_content = hint.height_no_padding().max(SHADOW_HEIGHT);
            let hint_width = hint.width();
            let (_rest, hint_area) = bounds.split_bottom(hint_height);

            let shadow_offset_x = Offset::x(hint_height_content / 2);
            let shadow_size = Offset::new(hint_width + theme::PADDING, hint_height_content)
                + shadow_offset_x * 2.0;
            // FIXME: hardcoded offset to properly center the shadow necessary due to
            // asymmetric insets of the HintContent::Instruction
            let shadow_anchor = hint_area.left_center() - shadow_offset_x - Offset::y(4);
            self.hint_shadow_area =
                Rect::snap(shadow_anchor, shadow_size, Alignment2D::CENTER_LEFT);
            hint.place(hint_area);
        }
        bounds
    }
    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        const LED_TOGGLE_DURATION: Duration = Duration::from_millis(3000);

        if self.led_color.is_some() {
            if self.is_alert() || animation_disabled() {
                // Alert: LED is always on, notification visible immediately
                if matches!(event, Event::Attach(_)) {
                    self.led_active = true;
                    self.notification_visible = true;
                    ctx.request_paint();
                }
            } else {
                match event {
                    Event::Attach(_) => {
                        // Start off, schedule turning on after LED_TOGGLE_DURATION
                        self.led_active = false;
                        self.notification_visible = false;
                        self.led_timer.start(ctx, LED_TOGGLE_DURATION);
                    }
                    Event::Timer(_) if self.led_timer.expire(event) => {
                        if !self.led_active {
                            // Turn on LED, make notification UI visible (permanently)
                            self.led_active = true;
                            self.notification_visible = true;
                            self.led_timer.start(ctx, LED_TOGGLE_DURATION);
                        } else {
                            // Turn off LED, but notification UI stays visible
                            self.led_active = false;
                        }
                        ctx.request_paint();
                    }
                    _ => {}
                }
            }
        }
        None
    }
    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let active_color = if self.led_active {
            self.led_color
        } else {
            None
        };

        if self.background_image {
            // Only render hint shadow when notification is visible
            if self.notification_visible {
                render_pill_shaped_background(self.hint_shadow_area, target);
            }
        } else {
            // default homescreen
            ScreenBackground::new(active_color, None).render(target);
        }
        // Only render hint when notification has become visible
        if self.notification_visible {
            self.hint.render(target);
        }

        #[cfg(feature = "rgb_led")]
        target.set_led_state(LedState::Static(active_color.unwrap_or_else(Color::black)));
    }
}

/// Helper component that displays device name label, battery status, and
/// connection status indicator.
/// It is combined because the label is shown together with the fuel gauge and
/// connection indicator.
struct HomescreenHeader {
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
    /// Whether to show fuel gauge and connection indicator
    show_indicators: bool,
    /// Cached text width of the label
    text_width: i16,
    /// Animation for showing/hiding the label
    label_anim: Option<ShowLabelAnimation>,
    /// Cached label clipping window
    label_area: Rect,
    /// Cached pill-shaped background area
    label_shadow_area: Rect,
}

impl HomescreenHeader {
    pub const SUBCOMPONENTS_GAP: i16 = 16;
    const SHADOW_OFFSET_X: Offset = Offset::x(SHADOW_HEIGHT / 2);
    const SHADOW_ANCHOR: Point = Point::new(0, 21).ofs(Self::SHADOW_OFFSET_X.neg());

    pub fn new(label: TString<'static>, background_image: bool, show_info: bool) -> Self {
        let style = theme::firmware::TEXT_SMALL;
        let text_width = label.map(|text| style.text_font.text_width(text));
        let label_anim = Some(ShowLabelAnimation::new(text_width, background_image));

        Self {
            area: Rect::zero(),
            label: Label::left_aligned(label, style).top_aligned(),
            fuel_gauge: FuelGauge::always_icon_only(),
            connection_indicator: ConnectionIndicator::new_polled(),
            background_image,
            show_indicators: show_info,
            text_width,
            label_anim,
            label_area: Rect::zero(),
            label_shadow_area: Rect::zero(),
        }
    }
}

impl Component for HomescreenHeader {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        if self.show_indicators {
            let (fuel_gauge_area, _) = bounds.split_left(self.fuel_gauge.content_width());
            let connection_indicator_area = Rect::snap(
                fuel_gauge_area.right_center(),
                Offset::uniform(ConnectionIndicator::AREA_SIZE_NEEDED),
                Alignment2D::CENTER_LEFT,
            )
            .translate(Offset::x(Self::SUBCOMPONENTS_GAP))
            // Visually align with the fuel gauge icon
            .translate(Offset::y(-1));

            self.fuel_gauge.place(fuel_gauge_area);
            self.connection_indicator.place(connection_indicator_area);

            let label_area = {
                let anchor = if self.connection_indicator.connected {
                    connection_indicator_area.right_center()
                } else {
                    fuel_gauge_area.right_center()
                };
                Rect::snap(
                    anchor,
                    Offset::new(self.text_width, self.label.font().max_height),
                    Alignment2D::CENTER_LEFT,
                )
                .translate(Offset::x(Self::SUBCOMPONENTS_GAP))
                // Visually align with the fuel gauge icon
                .translate(Offset::y(1))
            };
            self.label_area = label_area;
            self.label.place(label_area);

            // pill background spans from off-screen left to cover the full status row
            let shadow_size =
                Offset::new(label_area.x1, SHADOW_HEIGHT) + Self::SHADOW_OFFSET_X * 2.0;
            self.label_shadow_area = Rect::from_top_left_and_size(Self::SHADOW_ANCHOR, shadow_size);
        } else {
            let label_area = Rect::snap(
                bounds.left_center(),
                Offset::new(self.text_width, self.label.font().max_height),
                Alignment2D::CENTER_LEFT,
            );
            self.label_area = label_area;
            self.label.place(label_area);
        }

        self.area = bounds;
        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if self.show_indicators {
            self.fuel_gauge.event(ctx, event);
            let connection_event = self.connection_indicator.event(ctx, event);
            if matches!(event, Event::Attach(_) | Event::PM(_)) || connection_event.is_some() {
                // TODO: could FuelGauge also return Some(()) on update?
                self.place(self.area);
                ctx.request_paint();
            }

            if let Some(label_anim) = &mut self.label_anim {
                label_anim.process_event(ctx, event);
            }
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if self.show_indicators {
            if let Some(animation) = &self.label_anim {
                let x_offset = animation.eval_offset();
                let shadow_offset = x_offset
                    + Offset::x(i16::lerp(
                        0,
                        -Self::SUBCOMPONENTS_GAP,
                        animation.hide_progress(),
                    ));
                if self.background_image {
                    target.with_origin(shadow_offset, &|target| {
                        render_pill_shaped_background(self.label_shadow_area, target);
                    });
                }
                target.in_clip(self.label_area, &|target| {
                    target.with_origin(x_offset, &|target| {
                        self.label.render(target);
                    });
                });
            }
            self.fuel_gauge.render(target);
            self.connection_indicator.render(target);
        } else {
            self.label.render(target);
        }
    }
}

static FIRST_BOOT: AtomicBool = AtomicBool::new(true);

struct ShowLabelAnimation {
    stopwatch: Stopwatch,
    timer: Timer,
    duration: Duration,
    label_width: i16,
    animating: bool,
    hidden: bool,
    /// When true, the label slides in/out. When false, it instantly
    /// shows/hides.
    animated: bool,
}

impl ShowLabelAnimation {
    const HIDE_AFTER: Duration = Duration::from_millis(3000);
    const MOVE_DURATION: Duration = Duration::from_millis(500);
    // width at which MOVE_DURATION applies exactly
    const REFERENCE_WIDTH: i16 = 200;

    pub fn new(label_width: i16, animated: bool) -> Self {
        // start with hidden by default but not on first boot
        let hidden = if FIRST_BOOT.swap(false, Ordering::Relaxed) {
            false
        } else {
            !animation_disabled()
        };

        let scaled_ms =
            (Self::MOVE_DURATION.to_millis() * label_width as u32) / Self::REFERENCE_WIDTH as u32;
        let duration = Duration::from_millis(scaled_ms);

        Self {
            stopwatch: Stopwatch::default(),
            timer: Timer::new(),
            duration,
            label_width,
            animating: false,
            hidden,
            animated,
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
        if animation_disabled() || !self.animated {
            if self.hidden && !self.animating {
                return Offset::x(-self.label_width);
            }
            return Offset::zero();
        }

        let pos = self.eval();
        Offset::x(i16::lerp(-self.label_width, 0, pos))
    }

    /// Returns 0.0 when label is fully visible, 1.0 when fully hidden.
    pub fn hide_progress(&self) -> f32 {
        if animation_disabled() || !self.animated {
            if self.hidden && !self.animating {
                return 1.0;
            }
            return 0.0;
        }
        1.0 - self.eval()
    }

    pub fn process_event(&mut self, ctx: &mut EventCtx, event: Event) {
        match event {
            Event::Attach(_) => {
                if !self.hidden {
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
                if self.animated {
                    self.stopwatch.start();
                    ctx.request_anim_frame();
                    self.animating = true;
                    self.hidden = false;
                } else {
                    // Instant hide
                    self.hidden = true;
                    ctx.request_paint();
                }
            }
            Event::Touch(TouchEvent::TouchStart(point)) => {
                // Only trigger animation at the top of the screen
                if point.y <= SCREEN.height() / 2 {
                    if self.animated {
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
                    } else {
                        // Instant show/hide
                        if self.hidden {
                            self.hidden = false;
                            self.timer.start(ctx, Self::HIDE_AFTER);
                            ctx.request_paint();
                        } else {
                            self.timer.start(ctx, Self::HIDE_AFTER);
                        }
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

fn render_pill_shaped_background<'s>(area: Rect, target: &mut impl Renderer<'s>) {
    const SHADOW_ALPHA: u8 = 230; // 90%
    shape::Bar::new(area)
        .with_bg(theme::BG)
        .with_fg(theme::BG)
        .with_radius(area.height() / 2)
        .with_alpha(SHADOW_ALPHA)
        .render(target);
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Homescreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Homescreen");
        t.child("status", &self.header);
        t.child("homebar", &self.action_bar);
    }
}
#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for HomescreenHeader {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("HomescreenStatus");
        t.child("label", &self.label);
        t.child("fuel_gauge", &self.fuel_gauge);
        t.child("connection_indicator", &self.connection_indicator);
    }
}
