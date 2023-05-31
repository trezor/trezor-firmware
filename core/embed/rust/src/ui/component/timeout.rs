use crate::{
    time::Duration,
    ui::{
        component::{Component, Event, EventCtx, TimerToken},
        geometry::Rect,
    },
};

pub struct Timeout {
    time_ms: u32,
    timer: Option<TimerToken>,
}

impl Timeout {
    pub fn new(time_ms: u32) -> Self {
        Self {
            time_ms,
            timer: None,
        }
    }
}

impl Component for Timeout {
    type Msg = ();

    fn place(&mut self, _bounds: Rect) -> Rect {
        Rect::zero()
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match event {
            // Set up timer.
            Event::Attach => {
                self.timer = Some(ctx.request_timer(Duration::from_millis(self.time_ms)));
                None
            }
            // Fire.
            Event::Timer(token) if Some(token) == self.timer => {
                self.timer = None;
                Some(())
            }
            _ => None,
        }
    }

    fn paint(&mut self) {}
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Timeout {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Timeout");
        t.int("time_ms", self.time_ms as i64);
    }
}
