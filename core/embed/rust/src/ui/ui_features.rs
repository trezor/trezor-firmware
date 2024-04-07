use crate::ui::geometry::Rect;
#[cfg(feature = "bootloader")]
use crate::{trezorhal::secbool::secbool, ui::display::Color};

pub trait UIFeaturesCommon {
    fn fadein() {}
    fn fadeout() {}

    const SCREEN: Rect;

    fn screen_fatal_error(title: &str, msg: &str, footer: &str);

    fn screen_boot_full();
}

#[cfg(feature = "bootloader")]
pub trait UIFeaturesBootloader {
    fn screen_welcome();

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

    fn screen_boot_empty(fading: bool);

    fn screen_wipe_progress(progress: u16, initialize: bool);

    fn screen_install_progress(progress: u16, initialize: bool, initial_setup: bool);

    fn screen_connect(initial_setup: bool);

    fn screen_wipe_success();

    fn screen_wipe_fail();
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
