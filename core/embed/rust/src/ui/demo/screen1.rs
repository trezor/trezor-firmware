use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    display::{font::Font, Color},
    event::TouchEvent,
    geometry::{Point, Rect},
    layout::obj::{ComponentMsgObj, LayoutObj},
    model_tt::{component::Frame, theme},
    shape,
    shape::Renderer,
};

use crate::time::{Duration, Stopwatch};

use crate::{
    error::Error,
    micropython::{gc::Gc, obj::Obj},
};
use pareen;

#[derive(Default)]
struct BallAnim {
    pub timer: Stopwatch,
}

impl BallAnim {
    const DURATION: f32 = 1.5;

    pub fn is_active(&self) -> bool {
        self.timer.is_running_within(Duration::from(Self::DURATION))
    }

    pub fn eval(&self) -> Point {
        let x_anim = pareen::constant(30.0).seq_ease_out(
            0.0,
            pareen::easer::functions::Cubic,
            Self::DURATION,
            pareen::constant(210.0),
        );

        let y_anim = pareen::constant(30.0).seq_ease_out(
            0.0,
            pareen::easer::functions::Bounce,
            Self::DURATION,
            pareen::constant(210.0),
        );

        let t = self.timer.elapsed().into();

        Point::new(x_anim.eval(t) as i16, y_anim.eval(t) as i16)
    }
}

#[derive(Default)]
struct TextAnim {
    pub timer: Stopwatch,
}

impl TextAnim {
    pub fn is_active(&self) -> bool {
        self.timer.is_running_within(Duration::from(3.4))
    }

    pub fn eval(&self) -> Point {
        let x_anim = pareen::constant(30.0)
            .seq_ease_in(
                0.0,
                pareen::easer::functions::Cubic,
                0.3,
                pareen::constant(240.0),
            )
            .seq_ease_out(
                2.5,
                pareen::easer::functions::Elastic,
                0.9,
                pareen::constant(30.0),
            );

        let t = self.timer.elapsed().into();

        Point::new(x_anim.eval(t) as i16, 120)
    }
}

pub struct Screen1 {
    ball_anim: BallAnim,
    text_anim: TextAnim,
}

impl Screen1 {
    pub fn new() -> Self {
        Self {
            ball_anim: Default::default(),
            text_anim: Default::default(),
        }
    }
}

impl Component for Screen1 {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match event {
            Event::Touch(TouchEvent::TouchStart(_)) => {
                self.ball_anim.timer.start();
                self.text_anim.timer.start();
            }
            _ => {}
        }

        if self.ball_anim.is_active() && self.text_anim.is_active() {
            ctx.request_anim_frame();
        }

        None
    }

    fn paint(&mut self) {}

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let r = Rect::new(Point::new(10, 30), Point::new(230, 230));
        shape::Bar::new(r)
            .with_bg(Color::rgb(0, 20, 40))
            .render(target);

        shape::Text::new(self.text_anim.eval(), "Touch to start")
            .with_font(Font::BOLD)
            .render(target);

        shape::Circle::new(self.ball_anim.eval(), 16)
            .with_bg(Color::rgb(96, 128, 128))
            .render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Screen1 {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Demo screen");
    }
}

impl ComponentMsgObj for Screen1 {
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!();
    }
}

pub fn build_screen1() -> Result<Gc<LayoutObj>, Error> {
    LayoutObj::new(Frame::left_aligned(
        theme::label_title(),
        "Animation Demo".into(),
        Screen1::new(),
    ))
}
