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
struct Anim {
    pub timer: Stopwatch,
}

impl Anim {
    const DURATION: f32 = 1.5;

    pub fn is_active(&self) -> bool {
        self.timer.is_running_within(Duration::from(Self::DURATION))
    }

    pub fn eval(&self) -> f32 {
        let anim = pareen::prop(5.0f32);

        let t: f32 = self.timer.elapsed().into();

        anim.eval(t)
    }
}

pub struct Screen3 {
    anim: Anim,
}

impl Screen3 {
    pub fn new() -> Self {
        Self {
            anim: Default::default(),
        }
    }
}

impl Component for Screen3 {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match event {
            Event::Attach => {
                self.anim.timer.start();
            }
            _ => {}
        }

        if self.anim.is_active() {
            ctx.request_anim_frame();
        }

        None
    }

    fn paint(&mut self) {}

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        const IMAGE_HOMESCREEN: &[u8] = include_res!("demo/minion.jpg");

        target.in_clip(
            Rect::new(Point::new(35, 35), Point::new(206, 206)),
            &mut |target| {
                shape::JpegImage::new(Point::zero(), IMAGE_HOMESCREEN).render(target);
            },
        );

        shape::FancyOverlay::new(Point::new(120, 120), self.anim.eval()).render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Screen3 {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Demo screen");
    }
}

impl ComponentMsgObj for Screen3 {
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!();
    }
}

pub fn build_screen3() -> Result<Gc<LayoutObj>, Error> {
    LayoutObj::new(Frame::left_aligned(
        theme::label_title(),
        "Animation Demo".into(),
        Screen3::new(),
    ))
}
