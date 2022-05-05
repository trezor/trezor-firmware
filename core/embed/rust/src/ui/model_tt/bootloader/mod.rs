use core::slice;

use crate::trezorhal::io::{io_touch_read, io_touch_unpack_x, io_touch_unpack_y};
use crate::ui::component::{Component, Event, EventCtx};
use crate::ui::display;
use crate::ui::event::TouchEvent;
use crate::ui::model_tt::bootloader::theme::TTBootloaderTextTemp;
use crate::ui::model_tt::constant;
use cstr_core::CStr;

pub mod confirm;
mod connect;
mod fwinfo;
pub mod intro;
pub mod menu;
pub mod progress;
mod theme;
mod title;

use crate::ui::component::text::paragraphs::Paragraphs;
use crate::ui::geometry::LinearPlacement;
use crate::ui::model_tt::bootloader::connect::Connect;
use crate::ui::model_tt::theme::FONT_NORMAL;
use confirm::Confirm;
use fwinfo::FwInfo;
use intro::Intro;
use menu::Menu;
use progress::Progress;

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
        display::fadein();

        loop {
            let event = touch_eval();
            if let Some(e) = event {
                let mut ctx = EventCtx::new();
                let msg = self.frame.event(&mut ctx, Event::Touch(e));

                self.frame.paint();
                if let Some(message) = msg {
                    return message.return_to_c();
                }
            }
        }
    }
}

fn touch_eval() -> Option<TouchEvent> {
    let event = io_touch_read();
    if event == 0 {
        return None;
    }
    let event_type = event >> 24;
    let x = io_touch_unpack_x(event) as u32;
    let y = io_touch_unpack_y(event) as u32;
    let event = TouchEvent::new(event_type, x, y);

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
    let ptr = vendor_str as *const u8;
    let text = unsafe {
        CStr::from_bytes_with_nul_unchecked(slice::from_raw_parts(
            ptr,
            (vendor_str_len as usize) + 1,
        ))
        .to_str()
        .unwrap()
    };
    let version = unsafe { CStr::from_ptr(version).to_str().unwrap() };

    const ICON: Option<&'static [u8]> = Some(include_res!("model_tt/res/info.toif"));
    //const ICON: Option<&'static [u8]> = None;

    let title = if downgrade {
        "Downgrade firmware"
    } else if vendor {
        "Vendor change"
    } else {
        "Update firmware"
    };

    let message = Paragraphs::new()
        .add::<TTBootloaderTextTemp>(FONT_NORMAL, "Install firmware by")
        .add::<TTBootloaderTextTemp>(FONT_NORMAL, text)
        .add::<TTBootloaderTextTemp>(FONT_NORMAL, version)
        .with_placement(LinearPlacement::vertical().align_at_start());

    let mut frame = Confirm::new(title, ICON, message);

    if vendor || downgrade {
        frame.add_warning("Seed will be erased!");
    }

    let mut layout = BootloaderLayout::new(frame);
    return layout.process();
}

#[no_mangle]
extern "C" fn screen_wipe_confirm() -> u32 {
    const ICON: Option<&'static [u8]> = Some(include_res!("model_tt/res/info.toif"));

    let message = Paragraphs::new()
        .add::<TTBootloaderTextTemp>(FONT_NORMAL, "Do you want to wipe the device?")
        .with_placement(LinearPlacement::vertical().align_at_start());

    let mut frame = Confirm::new("Wipe device", ICON, message);
    frame.add_warning("Seed will be erased!");

    let mut layout = BootloaderLayout::new(frame);
    return layout.process();
}

#[no_mangle]
extern "C" fn screen_menu(bld_version: *const cty::c_char) -> u32 {
    let bld_version = unsafe { CStr::from_ptr(bld_version).to_str().unwrap() };

    let mut layout = BootloaderLayout::new(Menu::new(bld_version));
    return layout.process();
}

#[no_mangle]
extern "C" fn screen_intro(
    bld_version: *const cty::c_char,
    vendor_str: *const cty::c_char,
    vendor_str_len: u8,
    version: *const cty::c_char,
) -> u32 {
    let ptr = vendor_str as *const u8;
    let vendor = unsafe {
        CStr::from_bytes_with_nul_unchecked(slice::from_raw_parts(
            ptr,
            (vendor_str_len as usize) + 1,
        ))
        .to_str()
        .unwrap()
    };
    let version = unsafe { CStr::from_ptr(version).to_str().unwrap() };
    let bld_version = unsafe { CStr::from_ptr(bld_version).to_str().unwrap() };

    let mut layout = BootloaderLayout::new(Intro::new(bld_version, vendor, version));
    return layout.process();
}

#[no_mangle]
extern "C" fn screen_progress(text: *const cty::c_char, progress: u16, initialize: bool) -> u32 {
    let text = unsafe { CStr::from_ptr(text).to_str().unwrap() };
    let mut frame = Progress::new(text, initialize);

    frame.place(constant::screen());
    frame.set_progress(progress);
    frame.paint();
    0
}

#[no_mangle]
extern "C" fn screen_connect() -> u32 {
    let mut frame = Connect::new("Waiting for host");

    frame.place(constant::screen());
    frame.paint();
    display::fadein();
    0
}

#[no_mangle]
extern "C" fn screen_fwinfo(fingerprint: *const cty::c_char) -> u32 {
    let fingerprint = unsafe {
        CStr::from_bytes_with_nul_unchecked(slice::from_raw_parts(fingerprint as *const u8, 64 + 1))
            .to_str()
            .unwrap()
    };

    let mut layout = BootloaderLayout::new(FwInfo::new(fingerprint));
    return layout.process();
}
