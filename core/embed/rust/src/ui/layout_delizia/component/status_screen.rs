use super::theme;
use crate::{
    strutil::TString,
    time::{Duration, Stopwatch},
    ui::{
        component::{paginated::SinglePage, Component, Event, EventCtx, Label, Timeout},
        constant::screen,
        display::{Color, Icon},
        geometry::{Alignment, Alignment2D, Insets, Point, Rect},
        lerp::Lerp,
        shape::{self, Renderer},
        util::animation_disabled,
    },
};

const ANIMATION_TIME_MS: u32 = 1200;
const TIMEOUT_MS: u32 = ANIMATION_TIME_MS + 2000;

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
            .is_running_within(Duration::from_millis(ANIMATION_TIME_MS))
    }

    pub fn eval(&self) -> f32 {
        if animation_disabled() {
            return ANIMATION_TIME_MS as f32 / 1000.0;
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

        let circle_scale2 = pareen::constant(0.0).seq_ease_out(
            0.8,
            easer::functions::Linear,
            0.2,
            pareen::constant(1.0),
        );

        const CIRCLE_DIAMETER_MAX: i16 = 170;
        const CIRCLE_DIAMETER_MIN: i16 = 80;

        let a = i16::lerp(
            CIRCLE_DIAMETER_MAX / 2,
            CIRCLE_DIAMETER_MIN / 2,
            circle_scale.eval(t),
        );

        let b = i16::lerp(CIRCLE_DIAMETER_MIN / 2, 0, circle_scale2.eval(t));

        if t > 0.8 {
            b
        } else {
            a
        }
    }

    pub fn get_circle_position(&self, t: f32, start: Point) -> Point {
        let circle_pos = pareen::constant(0.0).seq_ease_in_out(
            0.8,
            easer::functions::Linear,
            0.2,
            pareen::constant(1.0),
        );

        const CIRCLE_DIAMETER_MAX: i16 = 170;
        const CIRCLE_DIAMETER_MIN: i16 = 80;

        Point::lerp(start, Point::zero(), circle_pos.eval(t))
    }

    pub fn get_content2_opacity(&self, t: f32) -> u8 {
        let content_opacity = pareen::constant(0.0).seq_ease_in(
            1.0,
            easer::functions::Linear,
            0.2,
            pareen::constant(1.0),
        );

        u8::lerp(0, 255, content_opacity.eval(t))
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
pub struct StatusScreen {
    area: Rect,
    icon: Icon,
    icon_color: Color,
    circle_color: Color,
    dismiss_type: DismissType,
    anim: StatusAnimation,
    msg: Label<'static>,
}

enum DismissType {
    SwipeUp,
    Timeout(Timeout),
}

impl StatusScreen {
    fn new(
        icon: Icon,
        icon_color: Color,
        circle_color: Color,
        dismiss_style: DismissType,
        msg: TString<'static>,
    ) -> Self {
        Self {
            area: Rect::zero(),
            icon,
            icon_color,
            circle_color,
            dismiss_type: dismiss_style,
            anim: StatusAnimation::default(),
            msg: Label::new(msg, Alignment::Start, theme::TEXT_NORMAL).vertically_centered(),
        }
    }

    pub fn new_success(msg: TString<'static>) -> Self {
        Self::new(
            theme::ICON_SIMPLE_CHECKMARK30,
            theme::GREEN_LIME,
            theme::GREEN_LIGHT,
            DismissType::SwipeUp,
            msg,
        )
    }

    pub fn new_success_timeout(msg: TString<'static>) -> Self {
        Self::new(
            theme::ICON_SIMPLE_CHECKMARK30,
            theme::GREEN_LIME,
            theme::GREEN_LIGHT,
            DismissType::Timeout(Timeout::new(TIMEOUT_MS)),
            msg,
        )
    }

    pub fn new_neutral(msg: TString<'static>) -> Self {
        Self::new(
            theme::ICON_SIMPLE_CHECKMARK30,
            theme::GREY_EXTRA_LIGHT,
            theme::GREY_DARK,
            DismissType::SwipeUp,
            msg,
        )
    }

    pub fn new_neutral_timeout(msg: TString<'static>) -> Self {
        Self::new(
            theme::ICON_SIMPLE_CHECKMARK30,
            theme::GREY_EXTRA_LIGHT,
            theme::GREY_DARK,
            DismissType::Timeout(Timeout::new(TIMEOUT_MS)),
            msg,
        )
    }
}

impl Component for StatusScreen {
    type Msg = ();

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.msg.place(bounds);
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

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let t = self.anim.eval();

        let pos = self.anim.get_circle_position(t, self.area.center());

        let content_2_alpha = self.anim.get_content2_opacity(t);
        let content_1_alpha = 255 - content_2_alpha;

        shape::Circle::new(pos, self.anim.get_circle_radius(t))
            .with_fg(self.circle_color)
            .with_bg(theme::BLACK)
            .with_thickness(2)
            .with_alpha(content_1_alpha)
            .render(target);

        if self.anim.get_circle_radius(t) > 20 {
            shape::ToifImage::new(pos, self.icon.toif)
                .with_align(Alignment2D::CENTER)
                .with_fg(self.icon_color)
                .with_alpha(content_1_alpha)
                .render(target);
        }

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

        self.msg.render_with_alpha(target, content_2_alpha);
    }
}

impl SinglePage for StatusScreen {}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for StatusScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("StatusScreen");
        t.child("msg", &self.msg);
    }
}
