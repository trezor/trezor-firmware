use crate::ui::geometry::Rect;

#[cfg(feature = "ui_debug_overlay")]
use crate::ui::shape::Renderer;

/// A structure containing information to be displayed in the debug overlay
/// on the screen when the "ui_debug_overlay" feature is enabled.
#[cfg(feature = "ui_debug_overlay")]
pub struct DebugOverlay {
    /// Time (in microseconds) spent by the rendering functions.
    pub render_time: u64,

    /// Time (in microseconds) between two consecutive screen refreshes.
    /// This includes the time spent on rendering, as well as time used by
    /// other activities in Rust and MicroPython, such as event processing
    /// and animation calculations.
    pub refresh_time: u64,
}

pub trait CommonUI {
    fn fadein() {}
    fn fadeout() {}
    fn backlight_on() {}

    fn get_backlight_none() -> u8 {
        0
    }
    fn get_backlight_normal() -> u8 {
        0
    }
    fn get_backlight_low() -> u8 {
        0
    }
    fn get_backlight_dim() -> u8 {
        0
    }
    fn get_backlight_max() -> u8 {
        0
    }

    const SCREEN: Rect;

    fn screen_fatal_error(title: &str, msg: &str, footer: &str);

    fn screen_boot_stage_2(fade_in: bool);

    /// Renders a partially transparent overlay over the screen content
    /// using data from the `DebugOverlay` struct.
    #[cfg(feature = "ui_debug_overlay")]
    fn render_debug_overlay<'s>(target: &mut impl Renderer<'s>, info: DebugOverlay);
}
