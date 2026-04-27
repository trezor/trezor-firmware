use core::sync::atomic::{AtomicBool, Ordering};

use crate::{
    strutil::TString,
    time::{Duration, Instant, Stopwatch},
    ui::{
        component::{Component, Event, EventCtx, Label, Never, Timer},
        event::TouchEvent,
        geometry::{Alignment2D, Offset, Point, Rect},
        lerp::Lerp,
        shape::Renderer,
        util::animation_disabled,
    },
};

use super::{
    super::{
        super::component::{ConnectionIndicator, FuelGauge},
        constant::SCREEN,
        theme,
    },
    helpers::{render_pill_shaped_background, SHADOW_HEIGHT},
};

static FIRST_BOOT: AtomicBool = AtomicBool::new(true);

/// Helper component that displays device name label, battery status, and
/// connection status indicator.
/// It is combined because the label is shown together with the fuel gauge and
/// connection indicator.
pub(super) struct HomescreenHeader {
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
    const FG_Y_OFFSET: i16 = -1;
    const LABEL_Y_OFFSET: i16 = 1;

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
            // Visually align with the fuel gauge icon
            .translate(Offset::new(Self::SUBCOMPONENTS_GAP, Self::FG_Y_OFFSET));

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
                // Visually align with the fuel gauge icon
                .translate(Offset::new(Self::SUBCOMPONENTS_GAP, Self::LABEL_Y_OFFSET))
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
            Event::Attach(_)
                if !self.hidden => {
                    self.timer.start(ctx, Self::HIDE_AFTER);
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
            Event::Touch(TouchEvent::TouchStart(point))
                // Only trigger animation at the top of the screen
                if point.y <= SCREEN.height() / 2 => {
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
            _ => {}
        }
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
