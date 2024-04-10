use crate::ui::{
    component::base::Component, constant::screen, display, model_tr::component::WelcomeScreen,
};

use super::{component::ErrorScreen, constant};

pub fn screen_fatal_error(title: &str, msg: &str, footer: &str) {
    let mut frame = ErrorScreen::new(title.into(), msg.into(), footer.into());
    frame.place(constant::screen());
    frame.paint();
}

pub fn screen_boot_stage_2() {
    let mut frame = WelcomeScreen::new(false);
    frame.place(screen());
    display::sync();
    frame.paint();
    display::refresh();
}
