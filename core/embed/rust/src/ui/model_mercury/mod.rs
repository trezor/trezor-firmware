use super::{geometry::Rect, UIFeaturesCommon};
use crate::ui::model_mercury::theme::backlight;

#[cfg(feature = "bootloader")]
pub mod bootloader;
pub mod component;
pub mod constant;
pub mod theme;

pub mod cshape;
#[cfg(feature = "micropython")]
pub mod flow;
#[cfg(feature = "micropython")]
pub mod layout;
pub mod screens;

pub struct ModelMercuryFeatures;

impl UIFeaturesCommon for ModelMercuryFeatures {
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
