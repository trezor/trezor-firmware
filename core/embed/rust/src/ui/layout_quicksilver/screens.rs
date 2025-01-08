use crate::ui::{component::Component, constant::screen, display};

use super::{
    component::{ErrorScreen, WelcomeScreen},
    constant,
};

use crate::ui::{display::Color, shape::render_on_display};

pub fn screen_fatal_error(title: &str, msg: &str, footer: &str) {
    let mut frame = ErrorScreen::new(title.into(), msg.into(), footer.into());
    frame.place(constant::screen());

    render_on_display(None, Some(Color::black()), |target| {
        frame.render(target);
    });

    display::refresh();
}

pub fn screen_boot_stage_2() {
    let mut frame = WelcomeScreen::new();
    frame.place(screen());

    display::sync();

    render_on_display(None, Some(Color::black()), |target| {
        frame.render(target);
    });

    display::refresh();
}
