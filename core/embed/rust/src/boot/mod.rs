use crate::trezorhal::io::{io_touch_read};
use crate::ui::component::{Child, Component, Event, EventCtx};
use crate::ui::display::icon;
use crate::ui::model_tt::theme::{ICON_TREZOR_EMPTY, ICON_TREZOR_FULL, BLUE, BLACK, WHITE};
use crate::ui::model_tt::component::Homescreen;
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

pub struct RustLayout<F> {
    root: Child<F>,
    event_ctx: EventCtx,
    page_count: u16,
}

impl<F> RustLayout<F>
    where
        F: Component,
        // F::Msg: ReturnToC,
{
    pub fn new(root: F) -> Self {
        Self {
            root: Child::new(root),
            event_ctx: EventCtx::new(),
            page_count: 1,
        }
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

        // Drain any pending timers into the callback.
        // while let Some((token, deadline)) = inner.event_ctx.pop_timer() {
        //     let token = token.try_into();
        //     let deadline = deadline.try_into();
        //     if let (Ok(token), Ok(deadline)) = (token, deadline) {
        //         inner.timer_fn.call_with_n_args(&[token, deadline])?;
        //     } else {
        //         // Failed to convert token or deadline into `Obj`, skip.
        //     }
        // }

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

    pub fn process(&mut self)  {

        loop {
            let event = touch_eval();
            if let Some(e) = event {
                let msg = self.root.event(&mut self.event_ctx, Event::Touch(e));

                if let Some(_) = msg {
                    return;
                }
            }

            self.paint_if_requested();
        }
    }
}



#[no_mangle]
pub extern "C" fn boot_firmware(
    stage: cty::uint16_t
) {

    if stage == 0 {
        icon(constant::screen().center(), ICON_TREZOR_EMPTY, WHITE, BLACK);
    }else {
        icon(constant::screen().center(), ICON_TREZOR_FULL, WHITE, BLACK);

        let mut hs = Homescreen::new();

        let mut layout = RustLayout::new(hs);

        layout.process();

    }
}
