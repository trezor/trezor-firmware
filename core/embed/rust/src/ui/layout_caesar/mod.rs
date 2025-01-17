use super::{geometry::Rect, CommonUI};

#[cfg(feature = "bootloader")]
pub mod bootloader;
pub mod common_messages;
pub mod component;
#[cfg(feature = "micropython")]
pub mod component_msg_obj;
pub mod constant;
pub mod cshape;
mod screens;
pub mod theme;

pub struct UICaesar {}

#[cfg(feature = "micropython")]
pub mod ui_firmware;

impl CommonUI for UICaesar {
    const SCREEN: Rect = constant::SCREEN;

    fn screen_fatal_error(title: &str, msg: &str, footer: &str) {
        screens::screen_fatal_error(title, msg, footer);
    }

    fn screen_boot_stage_2() {
        screens::screen_boot_stage_2();
    }
}
