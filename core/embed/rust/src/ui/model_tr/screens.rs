#[cfg(feature = "micropython")]
use crate::micropython::buffer::StrBuffer;
use crate::ui::{
    component::base::Component, constant::screen, display, model_tr::component::WelcomeScreen,
};

use super::{component::ErrorScreen, constant};

#[cfg(not(feature = "micropython"))]
// SAFETY: Actually safe but see below
unsafe fn get_str(text: &str) -> &str {
    text
}
#[cfg(feature = "micropython")]
// SAFETY: The caller is responsible for ensuring that the StrBuffer does not
// escape the lifetime of the original &str.
unsafe fn get_str(text: &str) -> StrBuffer {
    unsafe { StrBuffer::from_ptr_and_len(text.as_ptr(), text.len()) }
}

pub fn screen_fatal_error(title: &str, msg: &str, footer: &str) {
    // SAFETY: these will get placed into `frame` which does not outlive this
    // function
    let title = unsafe { get_str(title) };
    let msg = unsafe { get_str(msg) };
    let footer = unsafe { get_str(footer) };

    let mut frame = ErrorScreen::new(title, msg, footer);
    frame.place(constant::screen());
    frame.paint();
}

#[no_mangle]
extern "C" fn screen_boot_full() {
    let mut frame = WelcomeScreen::new(false);
    frame.place(screen());
    display::sync();
    frame.paint();
    display::refresh();
}
