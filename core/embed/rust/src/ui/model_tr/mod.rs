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

#[cfg(feature = "micropython")]
pub mod ui_features_fw;

impl UIFeaturesCommon for ModelTRFeatures {
    const SCREEN: Rect = constant::SCREEN;

    fn screen_fatal_error(title: &str, msg: &str, footer: &str) {
        screens::screen_fatal_error(title, msg, footer);
    }

    fn screen_boot_stage_2() {
        screens::screen_boot_stage_2();
    }
}
