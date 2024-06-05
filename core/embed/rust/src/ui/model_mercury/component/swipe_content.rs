use crate::{
    time::{Duration, Stopwatch},
    ui::{
        component::{base::AttachType, Component, Event, EventCtx, SwipeDirection},
        display::Color,
        event::SwipeEvent,
        geometry::{Offset, Rect},
        lerp::Lerp,
        shape,
        shape::Renderer,
        util::animation_disabled,
    },
};

#[derive(Default, Clone)]
struct AttachAnimation {
    pub timer: Stopwatch,
}

impl AttachAnimation {
    const DURATION_MS: u32 = 500;
    pub fn is_active(&self) -> bool {
        if animation_disabled() {
            return false;
        }

        self.timer
            .is_running_within(Duration::from_millis(Self::DURATION_MS))
    }

    pub fn eval(&self) -> f32 {
        if animation_disabled() {
            return 1.0;
        }

        self.timer.elapsed().to_millis() as f32 / 1000.0
    }

    pub fn get_offset(&self, t: f32, attach_type: Option<AttachType>) -> Offset {
        let value = pareen::constant(0.0).seq_ease_in(
            0.0,
            easer::functions::Linear,
            Self::DURATION_MS as f32 / 1000.0,
            pareen::constant(1.0),
        );

        match attach_type {
            Some(AttachType::Swipe(dir)) => match dir {
                SwipeDirection::Up => {
                    Offset::lerp(Offset::new(0, 20), Offset::zero(), value.eval(t))
                }
                SwipeDirection::Down => {
                    Offset::lerp(Offset::new(0, -20), Offset::zero(), value.eval(t))
                }
                _ => Offset::zero(),
            },
            _ => Offset::zero(),
        }
    }

    pub fn get_opacity(&self, t: f32, attach_type: Option<AttachType>) -> u8 {
        let value = pareen::constant(0.0).seq_ease_in_out(
            0.0,
            easer::functions::Cubic,
            0.2,
            pareen::constant(1.0),
        );
        match attach_type {
            Some(AttachType::Swipe(SwipeDirection::Up))
            | Some(AttachType::Swipe(SwipeDirection::Down)) => {}
            _ => {
                return 255;
            }
        }
        u8::lerp(0, 255, value.eval(t))
    }

    pub fn start(&mut self) {
        self.timer.start();
    }

    pub fn reset(&mut self) {
        self.timer = Stopwatch::new_stopped();
    }
}

pub struct SwipeContent<T> {
    inner: T,
    bounds: Rect,
    progress: i16,
    dir: SwipeDirection,
    normal: Option<AttachType>,
    attach_animation: AttachAnimation,
    attach_type: Option<AttachType>,
}

impl<T: Component> SwipeContent<T> {
    pub fn new(inner: T) -> Self {
        Self {
            inner,
            bounds: Rect::zero(),
            progress: 0,
            dir: SwipeDirection::Up,
            normal: Some(AttachType::Swipe(SwipeDirection::Down)),
            attach_animation: AttachAnimation::default(),
            attach_type: None,
        }
    }

    pub fn with_normal_attach(self, attach_type: Option<AttachType>) -> Self {
        Self {
            normal: attach_type,
            ..self
        }
    }

    pub fn inner(&self) -> &T {
        &self.inner
    }
}

impl<T: Component> Component for SwipeContent<T> {
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bounds = self.inner.place(bounds);
        self.bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Event::Attach(attach_type) = event {
            self.progress = 0;
            if let AttachType::Initial = attach_type {
                self.attach_type = self.normal;
            } else {
                self.attach_type = Some(attach_type);
            }
            self.attach_animation.reset();
            ctx.request_anim_frame();
        }
        if let Event::Timer(EventCtx::ANIM_FRAME_TIMER) = event {
            if !animation_disabled() {
                if !self.attach_animation.timer.is_running() {
                    self.attach_animation.timer.start();
                }
                if self.attach_animation.is_active() {
                    ctx.request_anim_frame();
                    ctx.request_paint();
                }
            }
        }

        if let Event::Swipe(SwipeEvent::Move(dir, progress)) = event {
            match dir {
                SwipeDirection::Up | SwipeDirection::Down => {
                    self.dir = dir;
                    self.progress = progress;
                }
                _ => {}
            }
            ctx.request_paint();
            ctx.request_anim_frame();
        }

        match event {
            Event::Touch(_) => {
                if self.attach_animation.is_active() {
                    None
                } else {
                    self.inner.event(ctx, event)
                }
            }
            _ => self.inner.event(ctx, event),
        }
    }

    fn paint(&mut self) {
        self.inner.paint()
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let progress = self.progress as f32 / 1000.0;

        let shift = pareen::constant(0.0).seq_ease_out(
            0.0,
            easer::functions::Cubic,
            1.0,
            pareen::constant(1.0),
        );

        let offset = i16::lerp(0, 50, shift.eval(progress));

        let mask = u8::lerp(0, 255, shift.eval(progress));

        if self.progress > 0 {
            match self.dir {
                SwipeDirection::Up => {
                    let offset = Offset::y(-offset);
                    target.in_clip(self.bounds, &|target| {
                        target.with_origin(offset, &|target| {
                            self.inner.render(target);
                            shape::Bar::new(self.bounds)
                                .with_alpha(mask)
                                .with_fg(Color::black())
                                .with_bg(Color::black())
                                .render(target);
                        });
                    });
                }
                SwipeDirection::Down => {
                    let offset = Offset::y(offset);
                    target.with_origin(offset, &|target| {
                        self.inner.render(target);
                        shape::Bar::new(self.bounds)
                            .with_alpha(mask)
                            .with_fg(Color::black())
                            .with_bg(Color::black())
                            .render(target);
                    });
                }
                _ => {}
            };
        } else {
            let t = self.attach_animation.eval();
            let offset = self.attach_animation.get_offset(t, self.attach_type);
            let opacity = self.attach_animation.get_opacity(t, self.attach_type);

            if offset.x != 0 || offset.y != 0 {
                target.in_clip(self.bounds, &|target| {
                    target.with_origin(offset, &|target| {
                        self.inner.render(target);
                        shape::Bar::new(self.bounds)
                            .with_alpha(255 - opacity)
                            .with_fg(Color::black())
                            .with_bg(Color::black())
                            .render(target);
                    });
                });
            } else {
                // some components draw outside their bounds during animations
                // let them do that unless we are animating here
                self.inner.render(target);
                shape::Bar::new(self.bounds)
                    .with_alpha(255 - opacity)
                    .with_fg(Color::black())
                    .with_bg(Color::black())
                    .render(target);
            }
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for SwipeContent<T>
where
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("SwipeContent");
        t.child("content", &self.inner);
    }
}
