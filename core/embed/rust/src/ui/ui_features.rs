use crate::ui::geometry::Rect;

#[cfg(feature = "bootloader")]
use crate::trezorhal::secbool::secbool;

#[cfg(not(feature = "new_rendering"))]
use crate::ui::display::Color;

pub trait UIFeaturesCommon {
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

    fn screen_boot_stage_2();
}

#[cfg(feature = "bootloader")]
pub trait UIFeaturesBootloader {
    fn screen_welcome();

    #[cfg(not(feature = "new_rendering"))]
    fn bld_continue_label(bg_color: Color);

    fn screen_install_success(restart_seconds: u8, initial_setup: bool, complete_draw: bool);

    fn screen_install_fail();

    fn screen_install_confirm(
        vendor: &str,
        version: &str,
        fingerprint: &str,
        should_keep_seed: bool,
        is_newvendor: bool,
        version_cmp: i32,
    ) -> u32;

    fn screen_wipe_confirm() -> u32;

    fn screen_unlock_bootloader_confirm() -> u32;

    fn screen_unlock_bootloader_success();

    fn screen_menu(firmware_present: secbool) -> u32;

    fn screen_intro(bld_version: &str, vendor: &str, version: &str, fw_ok: bool) -> u32;

    fn screen_boot_stage_1(fading: bool);

    fn screen_wipe_progress(progress: u16, initialize: bool);

    fn screen_install_progress(progress: u16, initialize: bool, initial_setup: bool);

    fn screen_connect(initial_setup: bool);

    fn screen_wipe_success();

    fn screen_wipe_fail();

    #[cfg(feature = "new_rendering")]
    fn screen_boot(
        warning: bool,
        vendor_str: Option<&str>,
        version: [u8; 4],
        vendor_img: &'static [u8],
        wait: i32,
    );
}

#[cfg(all(
    feature = "model_mercury",
    not(feature = "model_tr"),
    not(feature = "model_tt")
))]
pub type ModelUI = crate::ui::model_mercury::ModelMercuryFeatures;

#[cfg(all(feature = "model_tr", not(feature = "model_tt")))]
pub type ModelUI = crate::ui::model_tr::ModelTRFeatures;

#[cfg(feature = "model_tt")]
pub type ModelUI = crate::ui::model_tt::ModelTTFeatures;
