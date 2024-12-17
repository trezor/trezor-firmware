use crate::ui::geometry::Rect;

pub trait CommonUI {
    fn fadein() {}
    fn fadeout() {}
    fn backlight_on() {}

    fn get_backlight_none() -> u8 {
        0
    }
    fn get_backlight_normal() -> u8 {
        0
    }
    fn get_backlight_low() -> u8 {
        0
    }
    fn get_backlight_dim() -> u8 {
        0
    }
    fn get_backlight_max() -> u8 {
        0
    }

    const SCREEN: Rect;

    fn screen_fatal_error(title: &str, msg: &str, footer: &str);

    fn screen_boot_stage_2();
}
