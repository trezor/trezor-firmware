use crate::ui::{component::Component, constant::screen, display};

use super::{
    component::{ErrorScreen, WelcomeScreen},
    constant,
};

pub fn screen_fatal_error(title: &str, msg: &str, footer: &str) {
    let mut frame = ErrorScreen::new(title.into(), msg.into(), footer.into());
    frame.place(constant::screen());
    frame.paint();
}

pub fn screen_boot_full() {
    let mut frame = WelcomeScreen::new(false);
    frame.place(screen());
    display::sync();
    frame.paint();
    display::refresh();
}
