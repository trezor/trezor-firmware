use crate::{
    time::Instant,
    ui::{
        component::{Child, Component, Event, EventCtx, TimerToken},
        constant, display,
        model::theme,
    },
};
use heapless::Vec;

#[cfg(feature = "button")]
use crate::trezorhal::io::{io_button_read, BTN_EVT_DOWN, BTN_EVT_UP, BTN_LEFT, BTN_RIGHT};

#[cfg(feature = "touch")]
use crate::trezorhal::io::io_touch_read;
use crate::ui::constant::screen;
#[cfg(feature = "touch")]
use crate::ui::event::TouchEvent;

#[cfg(feature = "button")]
use crate::ui::event::ButtonEvent;

#[cfg(feature = "touch")]
fn touch_eval() -> Option<TouchEvent> {
    let event = io_touch_read();
    if event == 0 {
        return None;
    }
    let event_type = event >> 24;
    let ex = ((event >> 12) & 0xFFF) as i16;
    let ey = (event & 0xFFF) as i16;

    let (exr, eyr) = match display::orientation() {
        90 => (ey, constant::WIDTH - ex),
        180 => (constant::WIDTH - ex, constant::HEIGHT - ey),
        270 => (constant::HEIGHT - ey, ex),
        _ => (ex, ey),
    };

    let event = TouchEvent::new(event_type, exr as _, eyr as _);

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
    #[cfg(feature = "backlight")]
    backlight_level: u16,
    clear: bool,
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
            #[cfg(feature = "backlight")]
            backlight_level: theme::BACKLIGHT_NORMAL,
            clear: true,
        };
        instance.event(Event::Attach);
        instance
    }

    pub fn inner(&self) -> &F {
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

    pub fn process(&mut self) -> F::Msg {
        #[cfg(feature = "backlight")]
        display::fade_backlight(theme::BACKLIGHT_NONE);
        if self.clear {
            display::rect_fill(screen(), theme::BG);
        }
        self.paint_if_requested();
        display::refresh();

        #[cfg(feature = "backlight")]
        display::fade_backlight(self.backlight_level);

        self.eventloop()
    }

    fn eventloop(&mut self) -> F::Msg {
        loop {
            if let Some(msg) = self.process_touch() {
                return msg;
            }
            if let Some(msg) = self.process_buttons() {
                return msg;
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
                    return result;
                }
            }

            self.paint_if_requested();
            display::refresh();
        }
    }

    #[cfg(feature = "touch")]
    fn process_touch(&mut self) -> Option<<F as Component>::Msg> {
        let event = touch_eval();
        if let Some(e) = event {
            return self.event(Event::Touch(e));
        }
        None
    }
    #[cfg(not(feature = "touch"))]
    fn process_touch(&mut self) -> Option<<F as Component>::Msg> {
        None
    }

    #[cfg(feature = "button")]
    fn process_buttons(&mut self) -> Option<<F as Component>::Msg> {
        let evt = io_button_read();
        if (evt & (BTN_EVT_DOWN | BTN_EVT_UP)) != 0 {
            let etype = (evt >> 24) & 0x3; // button down/up
            let mut en = evt & 0xFFFF; // button number
            if display::orientation() == 180 {
                en = if en == BTN_LEFT { BTN_RIGHT } else { BTN_LEFT };
            }
            let e = ButtonEvent::new(etype, en);

            if let Ok(event) = e {
                return self.event(Event::Button(event));
            }
        }
        None
    }
    #[cfg(not(feature = "button"))]
    fn process_buttons(&mut self) -> Option<<F as Component>::Msg> {
        None
    }

    pub fn process_and_finish(&mut self) {
        self.paint_if_requested();
    }
}
