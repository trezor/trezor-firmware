//! Reexporting the `screens` module according to the
//! current feature (Trezor model)

use cty::int32_t;
use heapless::String;
use num_traits::ToPrimitive;
use crate::trezorhal::io::io_touch_read;
use crate::ui::component::{Component, Event, EventCtx, Label, Never};
use crate::ui::constant::screen;
use crate::ui::display;
use crate::ui::display::Icon;
use crate::ui::event::TouchEvent;
use crate::ui::model_tt::component::bl_confirm::{Confirm, ConfirmTitle};
use crate::ui::model_tt::component::{Button, ErrorScreen};
use crate::ui::model_tt::constant;
use crate::ui::model_tt::theme::{BACKLIGHT_DIM, BACKLIGHT_NORMAL};
use crate::ui::model_tt::theme::bootloader::{BLD_WIPE_COLOR, button_wipe_cancel, button_wipe_confirm, FIRE40, TEXT_WIPE_NORMAL};
#[cfg(all(feature = "model_tr", not(feature = "model_tt")))]
pub use super::model_tr::screens::*;
#[cfg(feature = "model_tt")]
pub use super::model_tt::screens::*;
use crate::ui::util::from_c_str;

#[no_mangle]
extern "C" fn screen_fatal_error_rust(
    title: *const cty::c_char,
    msg: *const cty::c_char,
    footer: *const cty::c_char,
) {
    let title = unsafe { from_c_str(title) }.unwrap_or("");
    let msg = unsafe { from_c_str(msg) }.unwrap_or("");
    let footer = unsafe { from_c_str(footer) }.unwrap_or("");

    screen_fatal_error(title, msg, footer);
}

pub trait ReturnToC {
    fn return_to_c(self) -> u32;
}

impl ReturnToC for Never {
    fn return_to_c(self) -> u32 {
        unreachable!()
    }
}

impl<T> ReturnToC for T
    where
        T: ToPrimitive,
{
    fn return_to_c(self) -> u32 {
        self.to_u32().unwrap()
    }
}


fn fadein() {
    display::fade_backlight_duration(BACKLIGHT_NORMAL, 150);
}

fn fadeout() {
    display::fade_backlight_duration(BACKLIGHT_DIM, 150);
}


fn touch_eval() -> Option<TouchEvent> {
    let event = io_touch_read();
    if event == 0 {
        return None;
    }
    let event_type = event >> 24;
    let ex = ((event >> 12) & 0xFFF) as i16;
    let ey = (event & 0xFFF) as i16;

    TouchEvent::new(event_type, ex as _, ey as _).ok()
}


fn run<F>(frame: &mut F) -> u32
    where
        F: Component,
        F::Msg: ReturnToC,
{
    frame.place(constant::screen());
    fadeout();
    display::sync();
    frame.paint();
    display::refresh();
    fadein();

    loop {
        let event = touch_eval();
        if let Some(e) = event {
            let mut ctx = EventCtx::new();
            let msg = frame.event(&mut ctx, Event::Touch(e));

            if let Some(message) = msg {
                return message.return_to_c();
            }
            display::sync();
            frame.paint();
            display::refresh();
        }
    }
}

fn show<F>(frame: &mut F, fading: bool)
    where
        F: Component,
{
    frame.place(screen());
    if fading {
        fadeout()
    };
    display::sync();
    frame.paint();
    display::refresh();
    if fading {
        fadein()
    };
}

#[no_mangle]
extern "C" fn sdtest_init(
    success: int32_t,
    failure: int32_t,
) -> u32 {

    let icon = Icon::new(FIRE40);

    let mut s: String<50> = String::new();
    unwrap!(s.push_str("Success: "));
    unwrap!(s.push_str(inttostr!(success)));
    unwrap!(s.push_str("\n"));
    unwrap!(s.push_str("Fail: "));
    unwrap!(s.push_str(inttostr!(failure)));
    unwrap!(s.push_str("\n"));
    unwrap!(s.push_str("Total: "));
    unwrap!(s.push_str(inttostr!(failure+success)));
    unwrap!(s.push_str("\n"));

    let msg = Label::centered(
        s.as_str(),
        TEXT_WIPE_NORMAL,
    );
    // let alert = Label::centered("SEED AND FIRMWARE\nWILL BE ERASED!", TEXT_WIPE_BOLD);

    let right = Button::with_text("RESET+TEST").styled(button_wipe_confirm());
    let left = Button::with_text("TEST").styled(button_wipe_cancel());

    let mut frame =
        Confirm::new(BLD_WIPE_COLOR, left, right, ConfirmTitle::Icon(icon), msg);

    run(&mut frame)

}

#[no_mangle]
extern "C" fn sdtest_update(
    success: int32_t,
    failure: int32_t,
) {


    let mut s: String<50> = String::new();
    unwrap!(s.push_str("Success: "));
    unwrap!(s.push_str(inttostr!(success)));
    unwrap!(s.push_str("\n"));
    unwrap!(s.push_str("Fail: "));
    unwrap!(s.push_str(inttostr!(failure)));
    unwrap!(s.push_str("\n"));
    unwrap!(s.push_str("Total: "));
    unwrap!(s.push_str(inttostr!(failure+success)));
    unwrap!(s.push_str("\n"));

    let mut frame = ErrorScreen::new("SD TEST RUNNING", s.as_str(), "Please wait");
    show(&mut frame, false);
}
