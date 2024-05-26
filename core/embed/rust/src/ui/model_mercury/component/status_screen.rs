use crate::{
    time::{Duration, Stopwatch},
    ui::{
        component::{Component, Event, EventCtx, Timeout},
        constant::screen,
        display::{Color, Icon},
        geometry::{Alignment2D, Insets, Rect},
        lerp::Lerp,
        shape,
        shape::Renderer,
        util::animation_disabled,
    },
};

use super::theme;

const TIMEOUT_MS: u32 = 2000;

#[derive(Default, Clone)]
struct StatusAnimation {
    pub timer: Stopwatch,
}

impl StatusAnimation {
    pub fn is_active(&self) -> bool {
        if animation_disabled() {
            return false;
        }

        self.timer
            .is_running_within(Duration::from_millis(TIMEOUT_MS))
    }

    pub fn eval(&self) -> f32 {
        if animation_disabled() {
            return TIMEOUT_MS as f32 / 1000.0;
        }
        self.timer.elapsed().to_millis() as f32 / 1000.0
    }

    pub fn get_instruction_opacity(&self, t: f32) -> u8 {
        let instruction_opacity = pareen::constant(0.0).seq_ease_in_out(
            0.0,
            easer::functions::Cubic,
            0.42,
            pareen::constant(1.0),
        );
        u8::lerp(0, 255, instruction_opacity.eval(t))
    }

    pub fn get_content_opacity(&self, t: f32) -> u8 {
        let content_opacity = pareen::constant(0.0).seq_ease_in_out(
            0.18,
            easer::functions::Cubic,
            0.2,
            pareen::constant(1.0),
        );

        u8::lerp(0, 255, content_opacity.eval(t))
    }

    pub fn get_circle_radius(&self, t: f32) -> i16 {
        let circle_scale = pareen::constant(0.0).seq_ease_out(
            0.2,
            easer::functions::Cubic,
            0.4,
            pareen::constant(1.0),
        );

        const CIRCLE_DIAMETER_MAX: i16 = 170;
        const CIRCLE_DIAMETER_MIN: i16 = 80;

        i16::lerp(
            CIRCLE_DIAMETER_MAX / 2,
            CIRCLE_DIAMETER_MIN / 2,
            circle_scale.eval(t),
        )
    }

    pub fn start(&mut self) {
        self.timer.start();
    }

    pub fn reset(&mut self) {
        self.timer = Stopwatch::new_stopped();
    }
}

/// Component showing status of an operation. Most typically embedded as a
/// content of a Frame and showing success (checkmark with a circle around).
#[derive(Clone)]
pub struct StatusScreen {
    area: Rect,
    icon: Icon,
    icon_color: Color,
    circle_color: Color,
    dismiss_type: DismissType,
    anim: StatusAnimation,
}

#[derive(Clone)]
enum DismissType {
    SwipeUp,
    Timeout(Timeout),
}

impl StatusScreen {
    fn new(icon: Icon, icon_color: Color, circle_color: Color, dismiss_style: DismissType) -> Self {
        Self {
            area: Rect::zero(),
            icon,
            icon_color,
            circle_color,
            dismiss_type: dismiss_style,
            anim: StatusAnimation::default(),
        }
    }

    pub fn new_success() -> Self {
        Self::new(
            theme::ICON_SIMPLE_CHECKMARK,
            theme::GREEN_LIME,
            theme::GREEN_LIGHT,
            DismissType::SwipeUp,
        )
    }

    pub fn new_success_timeout() -> Self {
        Self::new(
            theme::ICON_SIMPLE_CHECKMARK,
            theme::GREEN_LIME,
            theme::GREEN_LIGHT,
            DismissType::Timeout(Timeout::new(TIMEOUT_MS)),
        )
    }

    pub fn new_neutral() -> Self {
        Self::new(
            theme::ICON_SIMPLE_CHECKMARK,
            theme::GREY_EXTRA_LIGHT,
            theme::GREY_DARK,
            DismissType::SwipeUp,
        )
    }

    pub fn new_neutral_timeout() -> Self {
        Self::new(
            theme::ICON_SIMPLE_CHECKMARK,
            theme::GREY_EXTRA_LIGHT,
            theme::GREY_DARK,
            DismissType::Timeout(Timeout::new(TIMEOUT_MS)),
        )
    }
}

impl Component for StatusScreen {
    type Msg = ();

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Event::Attach(_) = event {
            self.anim.start();
            ctx.request_paint();
            ctx.request_anim_frame();
        }
        if let Event::Timer(EventCtx::ANIM_FRAME_TIMER) = event {
            if self.anim.is_active() {
                ctx.request_anim_frame();
                ctx.request_paint();
            }
        }

        if let DismissType::Timeout(ref mut timeout) = self.dismiss_type {
            if timeout.event(ctx, event).is_some() {
                return Some(());
            }
        }

        None
    }

    fn paint(&mut self) {
        todo!()
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let t = self.anim.eval();

        shape::Circle::new(self.area.center(), self.anim.get_circle_radius(t))
            .with_fg(self.circle_color)
            .with_bg(theme::BLACK)
            .with_thickness(2)
            .render(target);
        shape::ToifImage::new(self.area.center(), self.icon.toif)
            .with_align(Alignment2D::CENTER)
            .with_fg(self.icon_color)
            .render(target);

        //content + header cover
        shape::Bar::new(self.area.outset(Insets::top(self.area.y0)))
            .with_fg(theme::BLACK)
            .with_bg(theme::BLACK)
            .with_alpha(255 - self.anim.get_content_opacity(t))
            .render(target);

        //instruction cover
        shape::Bar::new(screen().inset(Insets::top(self.area.y1)))
            .with_fg(theme::BLACK)
            .with_bg(theme::BLACK)
            .with_alpha(255 - self.anim.get_instruction_opacity(t))
            .render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for StatusScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("StatusScreen");
    }
}
