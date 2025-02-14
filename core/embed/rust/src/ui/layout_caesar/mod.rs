use super::{geometry::Rect, CommonUI};

#[cfg(feature = "ui_debug_overlay")]
use super::{shape, DebugOverlay};

#[cfg(feature = "bootloader")]
pub mod bootloader;

#[cfg(feature = "prodtest")]
pub mod prodtest;

pub mod common_messages;
pub mod component;
#[cfg(feature = "micropython")]
pub mod component_msg_obj;
pub mod constant;
pub mod cshape;
pub mod fonts;
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

    fn screen_boot_stage_2(fade_in: bool) {
        screens::screen_boot_stage_2(fade_in);
    }

    #[cfg(feature = "ui_debug_overlay")]
    fn render_debug_overlay<'s>(_target: &mut impl shape::Renderer<'s>, _info: DebugOverlay) {
        // Not implemented
    }
}
