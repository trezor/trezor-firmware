use super::{geometry::Rect, CommonUI};

#[cfg(any(
    feature = "ui_debug_overlay",
    feature = "ui_performance_overlay",
    feature = "ui_dev_overlay"
))]
use super::shape;

#[cfg(any(feature = "ui_debug_overlay", feature = "ui_dev_overlay"))]
use super::{display::Color, geometry::Offset};

#[cfg(feature = "ui_performance_overlay")]
use super::PerformanceOverlay;

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

#[cfg(any(feature = "ui_debug_overlay", feature = "ui_dev_overlay"))]
const OVERLAY_MARKER_SIZE: Offset = Offset::uniform(constant::SCREEN.width() / 30);

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

    #[cfg(feature = "ui_debug_overlay")]
    fn render_debug_overlay<'s>(target: &mut impl shape::Renderer<'s>) {
        let r = Rect::from_top_right_and_size(Self::SCREEN.top_right(), OVERLAY_MARKER_SIZE);
        shape::Bar::new(r)
            .with_bg(Color::rgb(255, 0, 0))
            .render(target);
    }

    #[cfg(feature = "ui_performance_overlay")]
    fn render_performance_overlay<'s>(
        _target: &mut impl shape::Renderer<'s>,
        _info: PerformanceOverlay,
    ) {
        // Not implemented
    }

    #[cfg(feature = "ui_dev_overlay")]
    fn render_dev_overlay<'s>(target: &mut impl shape::Renderer<'s>) {
        let r = Rect::from_top_left_and_size(Self::SCREEN.top_left(), OVERLAY_MARKER_SIZE);
        shape::Bar::new(r)
            .with_bg(Color::rgb(0, 255, 0))
            .render(target);
    }
}
