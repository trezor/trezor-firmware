use super::{geometry::Rect, UIFeaturesCommon};

#[cfg(feature = "bootloader")]
pub mod bootloader;
pub mod component;
pub mod constant;
pub mod theme;

#[cfg(feature = "micropython")]
pub mod flow;
#[cfg(feature = "micropython")]
pub mod layout;
pub mod screens;
pub mod shapes;

pub struct ModelMercuryFeatures;

impl UIFeaturesCommon for ModelMercuryFeatures {
    fn fadein() {
        #[cfg(feature = "backlight")]
        crate::ui::display::fade_backlight_duration(theme::backlight::get_backlight_normal(), 150);
    }

    fn fadeout() {
        #[cfg(feature = "backlight")]
        crate::ui::display::fade_backlight_duration(theme::backlight::get_backlight_dim(), 150);
    }

    fn backlight_on() {
        #[cfg(feature = "backlight")]
        crate::ui::display::set_backlight(theme::backlight::get_backlight_normal());
    }

    const SCREEN: Rect = constant::SCREEN;

    fn screen_fatal_error(title: &str, msg: &str, footer: &str) {
        screens::screen_fatal_error(title, msg, footer);
    }

    fn screen_boot_stage_2() {
        screens::screen_boot_stage_2();
    }
}
