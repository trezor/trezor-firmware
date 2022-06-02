use crate::ui::component::{Component, Event, EventCtx};
use crate::ui::model_tr::constant;

pub mod intro;

use crate::time::Duration;
use crate::trezorhal::io::io_button_read;
use crate::trezorhal::time;
use crate::ui::event::ButtonEvent;
use intro::Intro;

pub trait ReturnToC {
    fn return_to_c(&self) -> u32;
}
pub struct BootloaderLayout<F> {
    frame: F,
}

impl<F> BootloaderLayout<F>
where
    F: Component,
    F::Msg: ReturnToC,
{
    pub fn new(frame: F) -> BootloaderLayout<F> {
        Self { frame }
    }

    pub fn process(&mut self) -> u32 {
        self.frame.place(constant::screen());
        self.frame.paint();
        // display::fadein();

        loop {
            let event = button_eval();
            if let Some(e) = event {
                let mut ctx = EventCtx::new();
                let msg = self.frame.event(&mut ctx, Event::Button(e));
                self.frame.paint();
            } else {
                let mut ctx = EventCtx::new();
                let msg = self
                    .frame
                    .event(&mut ctx, Event::Timer(EventCtx::ANIM_FRAME_TIMER));
                self.frame.paint();
            }
            time::sleep(Duration::from_millis(1));
        }
    }
}

fn button_eval() -> Option<ButtonEvent> {
    let btn = io_button_read();
    if btn == 0 {
        return None;
    }
    let event = ButtonEvent::new(btn >> 24, btn & 0xff);

    if let Ok(event) = event {
        return Some(event);
    }
    None
}

#[no_mangle]
extern "C" fn screen_install_confirm(
    vendor_str: *const cty::c_char,
    vendor_str_len: u8,
    version: *const cty::c_char,
    downgrade: bool,
    vendor: bool,
) -> u32 {
    0
}

#[no_mangle]
extern "C" fn screen_wipe_confirm() -> u32 {
    0
}

#[no_mangle]
extern "C" fn screen_menu(bld_version: *const cty::c_char) -> u32 {
    0
}

#[no_mangle]
extern "C" fn screen_intro(
    bld_version: *const cty::c_char,
    vendor_str: *const cty::c_char,
    vendor_str_len: u8,
    version: *const cty::c_char,
) -> u32 {
    let mut layout = BootloaderLayout::new(Intro::new());
    return layout.process();
}

#[no_mangle]
extern "C" fn screen_progress(text: *const cty::c_char, progress: u16, initialize: bool) -> u32 {
    0
}

#[no_mangle]
extern "C" fn screen_connect() -> u32 {
    0
}

#[no_mangle]
extern "C" fn screen_fwinfo(fingerprint: *const cty::c_char) -> u32 {
    0
}
