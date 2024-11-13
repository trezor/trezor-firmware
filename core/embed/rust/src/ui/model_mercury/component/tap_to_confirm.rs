use crate::{
    time::Duration,
    ui::{
        component::{Component, Event, EventCtx},
        display::{toif::Icon, Color},
        geometry::{Alignment2D, Offset, Rect},
        lerp::Lerp,
        shape,
        shape::Renderer,
        util::animation_disabled,
    },
};

use super::{theme, Button, ButtonContent, ButtonMsg};

use crate::{time::Stopwatch, ui::constant::screen};
use pareen;

#[derive(Default, Clone)]
struct TapToConfirmAnim {
    pub timer: Stopwatch,
}

impl TapToConfirmAnim {
    const DURATION_MS: u32 = 600;

    pub fn is_active(&self) -> bool {
        if animation_disabled() {
            return false;
        }

        self.timer
            .is_running_within(Duration::from_millis(Self::DURATION_MS))
    }

    pub fn is_finished(&self) -> bool {
        self.timer.elapsed() >= Duration::from_millis(Self::DURATION_MS)
    }
    pub fn eval(&self) -> f32 {
        if animation_disabled() {
            return 0.0;
        }
        self.timer.elapsed().to_millis() as f32 / 1000.0
    }

    pub fn get_parent_cover_opacity(&self, t: f32) -> u8 {
        let parent_cover_opacity = pareen::constant(0.0).seq_ease_in_out(
            0.0,
            easer::functions::Cubic,
            0.2,
            pareen::constant(1.0),
        );
        u8::lerp(0, 255, parent_cover_opacity.eval(t))
    }
    pub fn get_circle_scale(&self, t: f32) -> i16 {
        let circle_scale = pareen::constant(0.0).seq_ease_in_out(
            0.0,
            easer::functions::Cubic,
            0.58,
            pareen::constant(1.0),
        );
        i16::lerp(0, 80, circle_scale.eval(t))
    }
    pub fn get_circle_color(&self, t: f32, final_color: Color) -> Color {
        let circle_color = pareen::constant(0.0).seq_ease_in_out(
            0.0,
            easer::functions::Cubic,
            0.55,
            pareen::constant(1.0),
        );

        Color::lerp(Color::black(), final_color, circle_color.eval(t))
    }

    pub fn get_circle_opacity(&self, t: f32) -> u8 {
        let circle_opacity = pareen::constant(0.0).seq_ease_in_out(
            0.2,
            easer::functions::Cubic,
            0.8,
            pareen::constant(1.0),
        );
        u8::lerp(255, 0, circle_opacity.eval(t))
    }

    pub fn get_pad_opacity(&self, t: f32) -> u8 {
        let pad_opacity = pareen::constant(0.0).seq_ease_in_out(
            0.2,
            easer::functions::Cubic,
            0.4,
            pareen::constant(1.0),
        );
        u8::lerp(255, 0, pad_opacity.eval(t))
    }

    pub fn get_black_mask_scale(&self, t: f32) -> i16 {
        let black_mask_scale = pareen::constant(0.0).seq_ease_in_out(
            0.2,
            easer::functions::Cubic,
            0.8,
            pareen::constant(1.0),
        );
        i16::lerp(0, 400, black_mask_scale.eval(t))
    }

    pub fn start(&mut self) {
        self.timer.start();
    }

    pub fn reset(&mut self) {
        self.timer = Stopwatch::new_stopped();
    }
}

/// Component requesting a Tap to confirm action from a user. Most typically
/// embedded as a content of a Frame.
pub struct TapToConfirm {
    area: Rect,
    button: Button,
    circle_color: Color,
    circle_pad_color: Color,
    circle_inner_color: Color,
    mask_color: Color,
    icon: Icon,
    anim: TapToConfirmAnim,
}

impl TapToConfirm {
    pub fn new(
        circle_color: Color,
        circle_inner_color: Color,
        circle_pad_color: Color,
        mask_color: Color,
        icon: Icon,
    ) -> Self {
        let button = Button::new(ButtonContent::Empty).styled(theme::button_default());
        Self {
            area: Rect::zero(),
            circle_color,
            circle_inner_color,
            circle_pad_color,
            mask_color,
            button,
            icon,
            anim: TapToConfirmAnim::default(),
        }
    }
}

impl Component for TapToConfirm {
    type Msg = ();

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.button.place(Rect::snap(
            self.area.center(),
            Offset::uniform(80),
            Alignment2D::CENTER,
        ));
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let btn_msg = self.button.event(ctx, event);
        if let Some(ButtonMsg::Clicked) = btn_msg {
            if animation_disabled() {
                return Some(());
            }
            self.anim.start();
            ctx.request_anim_frame();
            ctx.request_paint();
        }

        if !animation_disabled() {
            if let Event::Timer(EventCtx::ANIM_FRAME_TIMER) = event {
                if self.anim.is_active() {
                    ctx.request_anim_frame();
                    ctx.request_paint();
                }
            }
            if self.anim.is_finished() {
                ctx.enable_swipe();
                return Some(());
            };
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        const PAD_RADIUS: i16 = 70;
        const PAD_THICKNESS: i16 = 20;
        const CIRCLE_RADIUS: i16 = 50;
        const INNER_CIRCLE_RADIUS: i16 = 40;
        const CIRCLE_THICKNESS: i16 = 2;

        let t = self.anim.eval();

        let center = self.area.center();

        shape::Bar::new(screen())
            .with_fg(theme::BLACK)
            .with_bg(theme::BLACK)
            .with_alpha(self.anim.get_parent_cover_opacity(t))
            .render(target);

        shape::Circle::new(center, PAD_RADIUS)
            .with_fg(self.circle_pad_color)
            .with_bg(theme::BLACK)
            .with_thickness(PAD_THICKNESS)
            .with_alpha(self.anim.get_pad_opacity(t))
            .render(target);
        shape::Circle::new(center, CIRCLE_RADIUS)
            .with_fg(self.circle_color)
            .with_bg(theme::BLACK)
            .with_thickness(CIRCLE_THICKNESS)
            .render(target);
        shape::Circle::new(center, CIRCLE_RADIUS - CIRCLE_THICKNESS)
            .with_fg(self.circle_pad_color)
            .with_bg(theme::BLACK)
            .with_thickness(CIRCLE_RADIUS - CIRCLE_THICKNESS - INNER_CIRCLE_RADIUS)
            .render(target);
        shape::Circle::new(center, self.anim.get_circle_scale(t))
            .with_fg(self.anim.get_circle_color(t, self.mask_color))
            .with_alpha(self.anim.get_circle_opacity(t))
            .render(target);
        shape::Circle::new(center, self.anim.get_black_mask_scale(t))
            .with_fg(theme::BLACK)
            .render(target);

        shape::ToifImage::new(center, self.icon.toif)
            .with_fg(theme::GREY)
            .with_alpha(255 - self.anim.get_parent_cover_opacity(t))
            .with_align(Alignment2D::CENTER)
            .render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for TapToConfirm {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("TapToConfirm");
        t.child("button", &self.button);
    }
}
