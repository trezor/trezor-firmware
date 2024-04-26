use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    geometry::{Offset, Point, Rect},
    layout::obj::{ComponentMsgObj, LayoutObj},
    model_tt::{component::Frame, theme},
    shape::{self, render_on_canvas, ImageBuffer, Renderer, Rgb565Canvas},
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
        let anim = pareen::prop(30.0f32);

        let t: f32 = self.timer.elapsed().into();

        anim.eval(t)
    }
}

pub struct Screen3 {
    anim: Anim,
    bg_image: ImageBuffer<Rgb565Canvas<'static>>,
}

impl Screen3 {
    const OVL_CENTER: Point = Point::new(120, 120);

    pub fn new() -> Self {
        let mut bg_image = unwrap!(ImageBuffer::new(Offset::new(171, 171)));

        render_on_canvas(bg_image.canvas(), None, |target| {
            const IMAGE_HOMESCREEN: &[u8] = include_res!("demo/minion.jpg");
            let offset = Self::OVL_CENTER - Offset::uniform(shape::UnlockOverlay::RADIUS);
            shape::JpegImage::new(-offset, IMAGE_HOMESCREEN).render(target);
        });

        Self {
            bg_image,
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
        let r = Rect::from_center_and_size(Self::OVL_CENTER, Offset::uniform(1))
            .expand(shape::UnlockOverlay::RADIUS);
        shape::RawImage::new(r, self.bg_image.view()).render(target);
        shape::UnlockOverlay::new(Self::OVL_CENTER, self.anim.eval()).render(target);
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
