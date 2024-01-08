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
    fn fadein() {
        #[cfg(feature = "backlight")]
        crate::ui::display::fade_backlight_duration(backlight::get_backlight_normal(), 150);
    }

    fn fadeout() {
        #[cfg(feature = "backlight")]
        crate::ui::display::fade_backlight_duration(backlight::get_backlight_normal(), 150);
    }

    fn backlight_on() {
        #[cfg(feature = "backlight")]
        crate::ui::display::set_backlight(backlight::get_backlight_normal());
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
