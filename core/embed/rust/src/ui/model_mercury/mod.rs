use super::{geometry::Rect, CommonUI};
use crate::ui::model_mercury::theme::backlight;

#[cfg(feature = "bootloader")]
pub mod bootloader;
pub mod component;
pub mod constant;
pub mod theme;

#[cfg(feature = "micropython")]
pub mod component_msg_obj;
pub mod cshape;
#[cfg(feature = "micropython")]
pub mod flow;
pub mod screens;
#[cfg(feature = "micropython")]
pub mod ui_firmware;

pub struct UIMercury;

impl CommonUI for UIMercury {
    #[cfg(feature = "backlight")]
    fn fadein() {
        crate::ui::display::fade_backlight_duration(backlight::get_backlight_normal(), 150);
    }

    #[cfg(feature = "backlight")]
    fn fadeout() {
        crate::ui::display::fade_backlight_duration(backlight::get_backlight_dim(), 150);
    }

    #[cfg(feature = "backlight")]
    fn backlight_on() {
        crate::ui::display::set_backlight(backlight::get_backlight_normal());
    }

    #[cfg(feature = "backlight")]
    fn get_backlight_none() -> u8 {
        backlight::get_backlight_none()
    }

    #[cfg(feature = "backlight")]
    fn get_backlight_normal() -> u8 {
        backlight::get_backlight_normal()
    }

    #[cfg(feature = "backlight")]
    fn get_backlight_low() -> u8 {
        backlight::get_backlight_low()
    }

    #[cfg(feature = "backlight")]
    fn get_backlight_dim() -> u8 {
        backlight::get_backlight_dim()
    }

    #[cfg(feature = "backlight")]
    fn get_backlight_max() -> u8 {
        backlight::get_backlight_max()
    }

    const SCREEN: Rect = constant::SCREEN;

    fn screen_fatal_error(title: &str, msg: &str, footer: &str) {
        screens::screen_fatal_error(title, msg, footer);
    }

    fn screen_boot_stage_2() {
        screens::screen_boot_stage_2();
    }
}
