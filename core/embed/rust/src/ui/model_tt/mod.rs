use super::{geometry::Rect, layout::simplified::SimplifiedFeatures};

#[cfg(feature = "bootloader")]
pub mod bootloader;
pub mod component;
pub mod constant;
pub mod theme;

#[cfg(feature = "micropython")]
pub mod layout;
pub mod screens;

pub struct ModelTTFeatures {}

impl SimplifiedFeatures for ModelTTFeatures {
    fn fadein() {
        #[cfg(feature = "backlight")]
        crate::ui::display::fade_backlight_duration(theme::BACKLIGHT_NORMAL, 150);
    }

    fn fadeout() {
        #[cfg(feature = "backlight")]
        crate::ui::display::fade_backlight_duration(theme::BACKLIGHT_DIM, 150);
    }

    const SCREEN: Rect = constant::SCREEN;
}
