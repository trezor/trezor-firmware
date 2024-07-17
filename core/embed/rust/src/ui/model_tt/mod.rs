use super::{geometry::Rect, UIFeaturesCommon};

#[cfg(feature = "bootloader")]
pub mod bootloader;
pub mod component;
pub mod constant;
pub mod theme;

#[cfg(feature = "backlight")]
use crate::ui::model_tt::theme::backlight;

#[cfg(feature = "micropython")]
pub mod layout;

use crate::ui::{
    layout::simplified::show,
    model_tt::component::{ErrorScreen, WelcomeScreen},
};

pub struct ModelTTFeatures;

impl UIFeaturesCommon for ModelTTFeatures {
    #[cfg(feature = "backlight")]
    fn fadein() {
        crate::ui::display::fade_backlight_duration(backlight::get_backlight_normal(), 150);
    }
    #[cfg(feature = "backlight")]
    fn fadeout() {
        crate::ui::display::fade_backlight_duration(backlight::get_backlight_normal(), 150);
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
        let mut frame = ErrorScreen::new(title.into(), msg.into(), footer.into());
        show(&mut frame, false);
    }

    fn screen_boot_stage_2() {
        let mut frame = WelcomeScreen::new(false);
        show(&mut frame, false);
    }
}
