use super::{geometry::Rect, CommonUI};
#[cfg(feature = "ui_performance_overlay")]
use super::{shape, PerformanceOverlay};

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
pub mod theme;

use crate::ui::layout::simplified::show;
use component::{ErrorScreen, WelcomeScreen};

pub struct UICaesar {}

#[cfg(feature = "micropython")]
pub mod ui_firmware;

impl CommonUI for UICaesar {
    const SCREEN: Rect = constant::SCREEN;

    fn screen_fatal_error(title: &str, msg: &str, footer: &str) {
        let mut frame = ErrorScreen::new(title.into(), msg.into(), footer.into());
        show(&mut frame, false);
    }

    fn screen_boot_stage_2(fade_in: bool) {
        let mut frame = WelcomeScreen::new(false);
        show(&mut frame, fade_in);
    }

    fn screen_update() {}

    #[cfg(feature = "ui_performance_overlay")]
    fn render_performance_overlay<'s>(
        _target: &mut impl shape::Renderer<'s>,
        _info: PerformanceOverlay,
    ) {
        // Not implemented
    }
}
