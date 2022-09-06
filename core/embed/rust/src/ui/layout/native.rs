use heapless::Vec;
use crate::time::{Instant};
use crate::trezorhal::io::{io_touch_read};
use crate::ui::component::{Child, Component, Event, EventCtx, TimerToken};
use crate::ui::constant;
use crate::ui::event::TouchEvent;


enum Iface {
    Touch,
}


fn touch_eval() -> Option<TouchEvent> {
    let event = io_touch_read();
    if event == 0 {
        return None;
    }
    let event_type = event >> 24;
    let x = (event >> 12) & 0xFFF;
    let y = (event >> 0) & 0xFFF;

    let event = TouchEvent::new(event_type, x, y);

    if let Ok(event) = event {
        return Some(event);
    }
    None
}


// pub trait ReturnToC {
//     fn return_to_c(&self) -> u32;
// }

const LAYOUT_MAX_TIMERS: usize = 16;

pub struct RustLayout<F> {
    root: Child<F>,
    event_ctx: EventCtx,
    timers: Vec<(TimerToken, Instant), LAYOUT_MAX_TIMERS>,
    page_count: u16,
}

impl<F> RustLayout<F>
    where
        F: Component,
// F::Msg: ReturnToC,
{
    pub fn new(root: F) -> Self {
        let mut instance = Self {
            root: Child::new(root),
            event_ctx: EventCtx::new(),
            timers: Vec::new(),
            page_count: 1,
        };
        instance.event(Event::Attach);
        instance
    }

    pub fn inner(&self) -> &F{
        self.root.inner()
    }

    /// Run an event pass over the component tree. After the traversal, any
    /// pending timers are drained into `self.timer_callback`. Returns `Err`
    /// in case the timer callback raises or one of the components returns
    /// an error, `Ok` with the message otherwise.
    fn event(&mut self, event: Event) -> Option<<F as Component>::Msg> {

        // Place the root component on the screen in case it was previously requested.
        if self.event_ctx.needs_place_before_next_event_or_paint() {
            self.root.place(constant::screen());
        }

        // Clear the leftover flags from the previous event pass.
        self.event_ctx.clear();

        // Send the event down the component tree. Bail out in case of failure.
        let msg = self.root.event(&mut self.event_ctx, event);

        // All concerning `Child` wrappers should have already marked themselves for
        // painting by now, and we're prepared for a paint pass.

        // Drain any pending timers.
        while let Some((token, duration)) = self.event_ctx.pop_timer() {

            let deadline = unwrap!(Instant::now().checked_add(duration), "Too long timer");
            unwrap!(self.timers.push((token, deadline)), "Timer queue full");
        }

        if let Some(count) = self.event_ctx.page_count() {
            self.page_count = count as u16;
        }

        msg
    }

    /// Run a paint pass over the component tree.
    fn paint_if_requested(&mut self) {

        // Place the root component on the screen in case it was previously requested.
        if self.event_ctx.needs_place_before_next_event_or_paint() {
            self.root.place(constant::screen());
        }

        self.root.paint();
    }

    pub fn process(&mut self) -> F::Msg  {

        loop {
            let event = touch_eval();
            if let Some(e) = event {
                let msg = self.event(Event::Touch(e));

                if let Some(result) = msg {
                    return result;
                }
            }

            let now = Instant::now();
            let mut new_timers: Vec<(TimerToken, Instant), LAYOUT_MAX_TIMERS> = Vec::new();
            let mut timer_events: Vec<TimerToken, LAYOUT_MAX_TIMERS> = Vec::new();

            for t in self.timers.iter() {
                if now > t.1 {
                    unwrap!(timer_events.push(t.0));
                } else {
                    unwrap!(new_timers.push(*t));
                }
            }
            self.timers = new_timers;

            for t in timer_events {
                let msg = self.event(Event::Timer(t));

                if let Some(result) = msg {
                   return result
                }
            }

            self.paint_if_requested();
        }
    }

    pub fn process_and_finish(&mut self) {
        self.paint_if_requested();
    }
}
