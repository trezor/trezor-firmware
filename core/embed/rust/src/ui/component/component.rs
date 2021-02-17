use core::time::Duration;

use staticvec::StaticVec;

use crate::ui::math::{Point, Rect};

pub trait Component {
    type Msg;

    fn widget(&mut self) -> &mut Widget;
    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg>;
    fn paint(&mut self);

    fn area(&mut self) -> Rect {
        self.widget().area
    }

    fn set_area(&mut self, area: Rect) {
        self.widget().area = area;
    }

    fn request_paint(&mut self) {
        self.widget().paint_requested = true;
    }

    fn paint_if_requested(&mut self) {
        if self.widget().paint_requested {
            self.widget().paint_requested = false;
            self.paint();
        }
    }
}

pub struct Widget {
    area: Rect,
    paint_requested: bool,
}

impl Widget {
    pub fn new(area: Rect) -> Self {
        Self {
            area,
            paint_requested: true,
        }
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum Event {
    TouchStart(Point),
    TouchMove(Point),
    TouchEnd(Point),
    Timer(TimerToken),
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub struct TimerToken(usize);

impl TimerToken {
    /// Value of an invalid (or missing) token.
    pub const INVALID: TimerToken = TimerToken(0);

    pub fn from_raw(raw: usize) -> Self {
        Self(raw)
    }

    pub fn into_raw(self) -> usize {
        self.0
    }
}

pub struct EventCtx {
    timers: StaticVec<(TimerToken, Duration), { Self::MAX_TIMERS }>,
    next_token: usize,
}

impl EventCtx {
    /// Maximum amount of timers requested in one event tick.
    const MAX_TIMERS: usize = 4;

    pub fn new() -> Self {
        Self {
            timers: StaticVec::new(),
            next_token: 1,
        }
    }

    pub fn request_timer(&mut self, deadline: Duration) -> TimerToken {
        let token = self.next_timer_token();
        self.timers.push((token, deadline));
        token
    }

    fn next_timer_token(&mut self) -> TimerToken {
        let token = TimerToken(self.next_token);
        self.next_token += 1;
        token
    }

    pub fn pop_timer(&mut self) -> Option<(TimerToken, Duration)> {
        self.timers.pop()
    }
}
