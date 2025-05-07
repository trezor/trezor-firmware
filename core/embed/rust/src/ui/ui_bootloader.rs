#[cfg(feature = "bootloader")]
use crate::trezorhal::secbool::secbool;
use crate::ui::component::Event;

pub trait BootloaderLayoutType {
    fn event(&mut self, event: Option<Event>) -> u32;
    fn show(&mut self);
    fn init_welcome() -> Self;
    fn init_menu(initial_setup: bool, firmware_present: secbool) -> Self;
    fn init_connect(initial_setup: bool, auto_update: bool) -> Self;
    #[cfg(feature = "ble")]
    fn init_pairing_mode(initial_setup: bool) -> Self;
}

#[cfg(feature = "bootloader")]
pub trait BootloaderUI {
    type CLayoutType: BootloaderLayoutType;

    fn screen_install_success(restart_seconds: u8, initial_setup: bool, complete_draw: bool);

    fn screen_install_fail();

    fn screen_install_confirm(
        vendor: &str,
        version: &str,
        fingerprint: &str,
        should_keep_seed: bool,
        is_newvendor: bool,
        is_newinstall: bool,
        version_cmp: i32,
    ) -> u32;

    fn screen_wipe_confirm() -> u32;

    fn screen_unlock_bootloader_confirm() -> u32;

    fn screen_unlock_bootloader_success();

    fn screen_intro(bld_version: &str, vendor: &str, version: &str, fw_ok: bool) -> u32;

    fn screen_boot_stage_1(fading: bool);

    fn screen_wipe_progress(progress: u16, initialize: bool);

    fn screen_install_progress(progress: u16, initialize: bool, initial_setup: bool);

    fn screen_wipe_success();

    fn screen_wipe_fail();

    fn screen_boot(
        warning: bool,
        vendor_str: Option<&str>,
        version: [u8; 4],
        vendor_img: &'static [u8],
        wait: i32,
    );

    #[cfg(feature = "ble")]
    fn screen_confirm_pairing(code: u32, initial_setup: bool) -> u32;

    #[cfg(feature = "ble")]
    fn screen_pairing_mode_finalizing(initial_setup: bool) -> u32;
}
