use super::{geometry::Rect, UIFeaturesCommon};

#[cfg(feature = "bootloader")]
pub mod bootloader;
pub mod common_messages;
pub mod component;
pub mod constant;
pub mod cshape;
#[cfg(feature = "micropython")]
pub mod layout;
mod screens;
pub mod theme;

pub struct ModelTRFeatures {}

impl UIFeaturesCommon for ModelTRFeatures {
    #[cfg(feature = "new_rendering")]
    type Display = crate::ui::shape::display::fb_display::Mono8;

    const SCREEN: Rect = constant::SCREEN;

    fn screen_fatal_error(title: &str, msg: &str, footer: &str) {
        screens::screen_fatal_error(title, msg, footer);
    }

    fn screen_boot_stage_2() {
        screens::screen_boot_stage_2();
    }
}
