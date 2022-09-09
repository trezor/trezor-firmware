use heapless::String;
use crate::micropython::obj::Obj;
use crate::micropython::{ffi, util};
use crate::trezorhal::storage::PinCallbackResult;
use crate::ui::constant::screen;
use crate::ui::display;
use crate::ui::geometry::{Point, Rect};
use crate::ui::model_tt::{constant, theme};

static mut PREV_SECONDS: u32 = 0xFFFFFFFF;
static mut PREV_PROGRESS: u32 = 0xFFFFFFFF;
static mut KEEPALIVE_CALLBACK: Option<Obj> = None;


pub fn show_pin_timeout(wait: u32, progress: u32, message: &str) -> PinCallbackResult {
    unsafe {

        if let Some(callback) = KEEPALIVE_CALLBACK {
            ffi::mp_call_function_0(callback);
        };

        if progress == 0 {
            if progress != PREV_PROGRESS {
                display::rect_fill(screen(), theme::BG);
                PREV_SECONDS = 0xFFFFFFFF;
            }

            display::text_center(Point::new(screen().center().x, 37), message, theme::FONT_BOLD, theme::FG, theme::BG);
        }

        if progress != PREV_PROGRESS {
            display::loader(progress as _, 0, theme::FG, theme::BG, None);
        }

        let mut s : String<16> = String::new();

        if wait != PREV_SECONDS {
            match wait {
                0 => {unwrap!(s.push_str("Done"))}
                1 => {unwrap!(s.push_str("1 second left"))}
                _ => {
                    let sec: String<16> = String::from(wait);
                    unwrap!(s.push_str(sec.as_str()));
                    unwrap!(s.push_str(" seconds left"))
                }
            };

            display::rect_fill(Rect::new(
                Point::new(0, constant::HEIGHT - 42),
                Point::new(constant::WIDTH, constant::HEIGHT - 42 + 25)),
                               theme::BG,
            );
            display::text_center(Point::new(screen().center().x, constant::HEIGHT - 22),
                                 s.as_str(),
                                 theme::FONT_BOLD,
                                 theme::FG,
                                 theme::BG,
            );
        }

        display::pixeldata_dirty();
        display::refresh();

        PREV_SECONDS = wait;
        PREV_PROGRESS = progress;


    }
    PinCallbackResult::Continue
}

#[no_mangle]
pub extern "C" fn set_keepalive_callback(obj: Obj) -> Obj {
    let block = || unsafe {
        KEEPALIVE_CALLBACK = Some(obj);
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
pub extern "C" fn remove_keepalive_callback() -> Obj  {
    let block = || unsafe {
        KEEPALIVE_CALLBACK = None;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}
