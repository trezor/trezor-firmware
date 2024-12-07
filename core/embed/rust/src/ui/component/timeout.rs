use crate::{
    time::Duration,
    ui::{
        component::{Component, Event, EventCtx, Timer},
        geometry::Rect,
        shape::Renderer,
    },
};

pub struct Timeout {
    time_ms: u32,
    timer: Timer,
}

impl Timeout {
    pub fn new(time_ms: u32) -> Self {
        Self {
            time_ms,
            timer: Timer::new(),
        }
    }
}

impl Component for Timeout {
    type Msg = ();

    fn place(&mut self, _bounds: Rect) -> Rect {
        Rect::zero()
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if matches!(event, Event::Attach(_)) {
            self.timer.start(ctx, Duration::from_millis(self.time_ms));
        }
        self.timer.expire(event).then_some(())
    }

    fn render<'s>(&'s self, _target: &mut impl Renderer<'s>) {}
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Timeout {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Timeout");
        t.int("time_ms", self.time_ms as i64);
    }
}
