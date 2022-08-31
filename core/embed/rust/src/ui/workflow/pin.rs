use crate::{
    error::Error,
    micropython::{buffer::StrBuffer, ffi, obj::Obj, util},
    trezorhal::storage::PinCallbackResult,
    ui::{
        constant::SCREEN,
        display::rect_fill,
        layout::simplified::show,
        model::{component::Progress, theme::BG},
        util::animation_disabled,
    },
};
use heapless::String;

static mut PREV_SECONDS: u32 = 0xFFFFFFFF;
static mut PREV_PROGRESS: u32 = 0xFFFFFFFF;
static mut PREV_PROGRESS_SHOWN: u32 = 0xFFFFFFFF;
static mut KEEPALIVE_CALLBACK: Option<Obj> = None;
static mut STARTED_WITH_EMPTY_LOADER: bool = false;

pub fn show_pin_timeout(wait: u32, progress: u32, message: &str) -> PinCallbackResult {
    // SAFETY: Single threaded access to static variables, StrBuffer is used in
    // layout that does    not outlive the string
    unsafe {
        if let Some(callback) = KEEPALIVE_CALLBACK {
            ffi::mp_call_function_0(callback);
        };

        let mut new_progress = false;

        if (progress == 0 && progress != PREV_PROGRESS) || STARTED_WITH_EMPTY_LOADER {
            new_progress = true;
            PREV_SECONDS = 0xFFFFFFFF;
            PREV_PROGRESS_SHOWN = progress;
            if !STARTED_WITH_EMPTY_LOADER {
                rect_fill(SCREEN, BG);
            }
        }

        let mut s: String<16> = String::new();

        if new_progress || wait != PREV_SECONDS || progress != PREV_PROGRESS {
            match wait {
                0 => {
                    unwrap!(s.push_str("Done"))
                }
                1 => {
                    unwrap!(s.push_str("1 second left"))
                }
                _ => {
                    let sec: String<16> = String::from(wait);
                    unwrap!(s.push_str(sec.as_str()));
                    unwrap!(s.push_str(" seconds left"))
                }
            };

            let mut m: String<32> = String::new();
            for c in message.chars() {
                unwrap!(m.push(c.to_ascii_uppercase()));
            }

            let m = StrBuffer::from_ptr_and_len(m.as_ptr(), message.len());
            let d = StrBuffer::from_ptr_and_len(s.as_ptr(), s.len());

            let mut frame = Progress::<StrBuffer>::new(m, false, d, |_| {
                // not used
                Err(Error::TypeError)
            });

            if !animation_disabled() || wait != PREV_SECONDS {
                frame.set_value(progress as u16);
                PREV_PROGRESS_SHOWN = progress;
            } else {
                frame.set_value(PREV_PROGRESS_SHOWN as u16);
            }

            show(&mut frame, false);
        }

        PREV_SECONDS = wait;
        PREV_PROGRESS = progress;
        STARTED_WITH_EMPTY_LOADER = false;
    }
    PinCallbackResult::Continue
}

#[no_mangle]
pub extern "C" fn set_keepalive_callback(obj: Obj) -> Obj {
    // SAFETY: Single threaded access
    let block = || unsafe {
        KEEPALIVE_CALLBACK = Some(obj);
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
pub extern "C" fn remove_keepalive_callback() -> Obj {
    // SAFETY: Single threaded access
    let block = || unsafe {
        KEEPALIVE_CALLBACK = None;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

pub fn draw_empty_loader(msg: StrBuffer, description: StrBuffer) {
    // SAFETY: Single threaded access
    unsafe {
        PREV_SECONDS = 0xFFFFFFFF;
        PREV_PROGRESS = 0;
        PREV_PROGRESS_SHOWN = 0;
        STARTED_WITH_EMPTY_LOADER = true;
    }

    rect_fill(SCREEN, BG);

    let mut frame = Progress::<StrBuffer>::new(msg, false, description, |_| {
        // not used
        Err(Error::TypeError)
    });

    show(&mut frame, false);
}
