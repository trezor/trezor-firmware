use super::component::{button::ButtonStyleSheet, label::LabelStyle};

pub const BACKLIGHT_NORMAL: i32 = 150;
pub const BACKLIGHT_LOW: i32 = 45;
pub const BACKLIGHT_DIM: i32 = 5;
pub const BACKLIGHT_NONE: i32 = 2;
pub const BACKLIGHT_MAX: i32 = 255;

pub fn label_default() -> LabelStyle {
    LabelStyle {
        font: -1,
        text_color: 0,
        background_color: 0,
    }
}

pub fn button_default() -> ButtonStyleSheet {
    todo!();
}
pub fn button_confirm() -> ButtonStyleSheet {
    todo!();
}
pub fn button_cancel() -> ButtonStyleSheet {
    todo!();
}
pub fn button_clear() -> ButtonStyleSheet {
    todo!();
}
