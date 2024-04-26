use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    display::Color,
    geometry::{Point, Rect},
    layout::obj::{ComponentMsgObj, LayoutObj},
    model_tt::{component::Frame, theme},
    shape,
    shape::Renderer,
};

use crate::{
    error::Error,
    micropython::{gc::Gc, obj::Obj},
};
use pareen;

use crate::time::Stopwatch;

#[derive(Default)]
struct LoaderAnim {
    pub timer: Stopwatch,
}

impl LoaderAnim {
    pub fn is_active(&self) -> bool {
        self.timer.is_running()
    }

    pub fn eval(&self) -> (i16, i16, i16) {
        let r1_anim = pareen::circle().cos().scale_min_max(60.0, 64.0).repeat(1.0);

        let r2_anim = pareen::circle()
            .cos()
            .scale_min_max(52.0, 58.0)
            .squeeze(0.0..=0.5)
            .repeat(0.5);

        let r3_anim = pareen::circle()
            .cos()
            .scale_min_max(40.0, 50.0)
            .squeeze(0.0..=2.0)
            .repeat(2.0);

        let t = self.timer.elapsed().into();

        (
            r1_anim.eval(t) as i16,
            r2_anim.eval(t) as i16,
            r3_anim.eval(t) as i16,
        )
    }
}

pub struct Screen1 {
    loader_anim: LoaderAnim,
}

impl Screen1 {
    pub fn new() -> Self {
        Self {
            loader_anim: Default::default(),
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
            Event::Attach => {
                self.loader_anim.timer.start();
            }
            _ => {}
        }

        if self.loader_anim.is_active() {
            ctx.request_anim_frame();
        }

        None
    }

    fn paint(&mut self) {}

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let bg_color = Color::rgb(40, 20, 0);

        let r = Rect::new(Point::new(10, 30), Point::new(230, 230));
        shape::Bar::new(r).with_bg(bg_color).render(target);

        let center = Point::new(120, 120);

        let (r1, r2, r3) = self.loader_anim.eval();

        shape::Circle::new(center, r1)
            .with_thickness(2)
            .with_bg(bg_color)
            .with_fg(Color::rgb(0, 120, 0))
            .render(target);

        shape::Circle::new(center, r2)
            .with_thickness(3)
            .with_bg(bg_color)
            .with_fg(Color::rgb(0, 120, 30))
            .render(target);

        shape::Circle::new(center, r3)
            .with_thickness(4)
            .with_bg(bg_color)
            .with_fg(Color::rgb(0, 120, 30))
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

pub fn build_screen2() -> Result<Gc<LayoutObj>, Error> {
    LayoutObj::new(Frame::left_aligned(
        theme::label_title(),
        "Animation Demo 2".into(),
        Screen1::new(),
    ))
}
