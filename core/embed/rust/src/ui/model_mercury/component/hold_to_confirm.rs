use crate::{
    time::Duration,
    translations::TR,
    ui::{
        component::{Component, Event, EventCtx},
        display::Color,
        geometry::{Alignment2D, Offset, Rect},
        lerp::Lerp,
        shape,
        shape::Renderer,
        util::animation_disabled,
    },
};

use super::{theme, Button, ButtonContent, ButtonMsg};

#[cfg(feature = "haptic")]
use crate::trezorhal::haptic::{self, HapticEffect};
use crate::{
    time::Stopwatch,
    ui::{
        component::Label,
        constant::screen,
        geometry::{Alignment, Point},
        model_mercury::theme::TITLE_HEIGHT,
    },
};
use pareen;

#[derive(Default, Clone)]
struct HoldToConfirmAnim {
    pub timer: Stopwatch,
}

impl HoldToConfirmAnim {
    const DURATION_MS: u32 = 2200;
    const LOCK_TIME_MS: u32 = 2000;

    pub fn is_active(&self) -> bool {
        if animation_disabled() {
            return false;
        }

        self.timer
            .is_running_within(Duration::from_millis(Self::DURATION_MS))
    }

    pub fn is_locked(&self) -> bool {
        if animation_disabled() {
            return false;
        }

        (!self
            .timer
            .is_running_within(Duration::from_millis(Self::LOCK_TIME_MS)))
            && self.timer.is_running()
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

    pub fn get_header_opacity(&self, t: f32) -> u8 {
        let header_opacity = pareen::constant(0.0).seq_ease_out(
            0.15,
            easer::functions::Cubic,
            0.2,
            pareen::constant(1.0),
        );

        u8::lerp(0, 255, header_opacity.eval(t))
    }

    pub fn get_header_opacity2(&self, t: f32) -> u8 {
        let header_opacity2 = pareen::constant(1.0).seq_ease_in(
            2.1,
            easer::functions::Cubic,
            0.1,
            pareen::constant(0.0),
        );

        u8::lerp(0, 255, header_opacity2.eval(t))
    }

    pub fn get_circle_opacity(&self, t: f32) -> u8 {
        let circle_opacity = pareen::constant(1.0).seq_ease_out(
            0.1,
            easer::functions::Cubic,
            0.1,
            pareen::constant(0.0),
        );

        u8::lerp(0, 255, circle_opacity.eval(t))
    }

    pub fn get_pad_color(&self, t: f32) -> Color {
        let pad_color = pareen::constant(0.0).seq_ease_in_out(
            0.1,
            easer::functions::Cubic,
            2.1,
            pareen::constant(1.0),
        );

        Color::lerp(theme::GREY_EXTRA_DARK, theme::GREEN, pad_color.eval(t))
    }

    pub fn get_circle_max_height(&self, t: f32) -> i16 {
        let circle_max_height = pareen::constant(0.0).seq_ease_in_out(
            0.25,
            easer::functions::Linear,
            1.95,
            pareen::constant(1.0),
        );

        i16::lerp(266, 0, circle_max_height.eval(t))
    }

    pub fn get_circle_radius(&self, t: f32) -> i16 {
        let circle_radius = pareen::constant(0.0).seq_ease_out(
            1.8,
            easer::functions::Cubic,
            0.4,
            pareen::constant(1.0),
        );

        i16::lerp(0, 100, circle_radius.eval(t))
    }

    pub fn get_haptic(&self, t: f32) -> u8 {
        let haptic = pareen::constant(0.0).seq_ease_in(
            0.0,
            easer::functions::Linear,
            Self::LOCK_TIME_MS as f32 / 1000.0,
            pareen::constant(1.0),
        );

        u8::lerp(0, 20, haptic.eval(t))
    }

    pub fn start(&mut self) {
        self.timer.start();
    }

    pub fn reset(&mut self) {
        self.timer = Stopwatch::new_stopped();
    }
}

/// Component requesting a hold to confirm action from a user. Most typically
/// embedded as a content of a Frame.
#[derive(Clone)]
pub struct HoldToConfirm {
    title: Label<'static>,
    area: Rect,
    button: Button,
    circle_color: Color,
    circle_pad_color: Color,
    circle_inner_color: Color,
    anim: HoldToConfirmAnim,
    finalizing: bool,
}

impl HoldToConfirm {
    pub fn new(circle_color: Color, circle_inner_color: Color) -> Self {
        let button = Button::new(ButtonContent::Empty)
            .styled(theme::button_default())
            .with_long_press(Duration::from_millis(2200))
            .without_haptics();
        Self {
            title: Label::new(
                TR::instructions__continue_holding.into(),
                Alignment::Start,
                theme::label_title_main(),
            )
            .vertically_centered(),
            area: Rect::zero(),
            circle_color,
            circle_pad_color: theme::GREY_EXTRA_DARK,
            circle_inner_color,
            button,
            anim: HoldToConfirmAnim::default(),
            finalizing: false,
        }
    }
}

impl Component for HoldToConfirm {
    type Msg = ();

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.button.place(Rect::snap(
            self.area.center(),
            Offset::uniform(80),
            Alignment2D::CENTER,
        ));
        self.title.place(screen().split_top(TITLE_HEIGHT).0);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let btn_msg = self.button.event(ctx, event);
        match btn_msg {
            Some(ButtonMsg::Pressed) => {
                if !self.anim.is_locked() {
                    self.anim.start();
                    ctx.request_anim_frame();
                    ctx.request_paint();
                    ctx.disable_swipe();
                    self.finalizing = false;
                }
            }
            Some(ButtonMsg::Released) => {
                if !self.anim.is_locked() {
                    self.anim.reset();
                    ctx.request_anim_frame();
                    ctx.request_paint();
                    ctx.enable_swipe();
                    self.finalizing = false;
                }
            }
            Some(ButtonMsg::Clicked) => {
                if animation_disabled() {
                    #[cfg(feature = "haptic")]
                    haptic::play(HapticEffect::HoldToConfirm);
                    return Some(());
                }
                if !self.anim.is_locked() {
                    self.finalizing = false;
                    self.anim.reset();
                    ctx.request_anim_frame();
                    ctx.request_paint();
                    ctx.enable_swipe();
                }
            }
            Some(ButtonMsg::LongPressed) => {
                self.finalizing = false;
                return Some(());
            }
            _ => (),
        }

        if let Event::Timer(EventCtx::ANIM_FRAME_TIMER) = event {
            if self.anim.is_active() {
                ctx.request_anim_frame();
                ctx.request_paint();

                if self.anim.is_locked() && !self.finalizing {
                    self.finalizing = true;
                    #[cfg(feature = "haptic")]
                    haptic::play(HapticEffect::HoldToConfirm);
                }
            } else if self.anim.is_locked() {
                return Some(());
            }
        }
        None
    }

    fn paint(&mut self) {
        unimplemented!()
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let elapsed = self.anim.eval();

        shape::Bar::new(screen())
            .with_fg(theme::BLACK)
            .with_bg(theme::BLACK)
            .with_alpha(self.anim.get_parent_cover_opacity(elapsed))
            .render(target);

        let center = self.area.center();

        const PROGRESS_CIRCLE_RADIUS: i16 = 88;
        const PAD_RADIUS: i16 = 70;
        const CIRCLE_RADIUS: i16 = 50;
        const INNER_CIRCLE_RADIUS: i16 = 40;
        const CIRCLE_THICKNESS: i16 = 2;

        if self.anim.get_parent_cover_opacity(elapsed) == 255 {
            shape::Circle::new(center, PROGRESS_CIRCLE_RADIUS)
                .with_fg(self.circle_inner_color)
                .with_bg(theme::BLACK)
                .with_thickness(CIRCLE_THICKNESS)
                .render(target);

            shape::Bar::new(Rect::new(
                Point::zero(),
                Point::new(screen().width(), self.anim.get_circle_max_height(elapsed)),
            ))
            .with_fg(theme::BLACK)
            .with_bg(theme::BLACK)
            .render(target);
        }

        let title_alpha = if self.anim.get_header_opacity2(elapsed) < 255 {
            self.anim.get_header_opacity2(elapsed)
        } else {
            self.anim.get_header_opacity(elapsed)
        };

        self.title.render_with_alpha(target, title_alpha);

        let pad_color = self.anim.get_pad_color(elapsed);
        let circle_alpha = self.anim.get_circle_opacity(elapsed);

        shape::Circle::new(center, PAD_RADIUS)
            .with_fg(pad_color)
            .with_bg(pad_color)
            .render(target);
        shape::Circle::new(center, CIRCLE_RADIUS)
            .with_fg(self.circle_color)
            .with_bg(self.circle_pad_color)
            .with_thickness(CIRCLE_THICKNESS)
            .with_alpha(circle_alpha)
            .render(target);
        shape::Circle::new(center, CIRCLE_RADIUS - CIRCLE_THICKNESS)
            .with_fg(self.circle_pad_color)
            .with_bg(self.circle_pad_color)
            .with_thickness(CIRCLE_RADIUS - CIRCLE_THICKNESS - INNER_CIRCLE_RADIUS)
            .with_alpha(circle_alpha)
            .render(target);
        shape::Circle::new(center, INNER_CIRCLE_RADIUS)
            .with_fg(self.circle_inner_color)
            .with_bg(theme::BLACK)
            .with_thickness(CIRCLE_THICKNESS)
            .with_alpha(circle_alpha)
            .render(target);

        shape::ToifImage::new(center, theme::ICON_SIGN.toif)
            .with_fg(theme::GREY)
            .with_alpha(circle_alpha)
            .with_align(Alignment2D::CENTER)
            .render(target);

        shape::Circle::new(center, self.anim.get_circle_radius(elapsed))
            .with_fg(theme::BLACK)
            .render(target);

        #[cfg(feature = "haptic")]
        {
            let hap = self.anim.get_haptic(elapsed);
            if hap > 0 && !self.anim.is_locked() {
                haptic::play_custom(hap as i8, 100);
            }
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for HoldToConfirm {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("StatusScreen");
        t.child("button", &self.button);
    }
}
