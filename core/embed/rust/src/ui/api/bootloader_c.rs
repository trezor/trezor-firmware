use crate::{
    strutil::hexlify,
    trezorhal::{
        layout_buf::{c_layout_t, LayoutBuffer},
        sysevent::{parse_event, sysevents_t},
    },
    ui::{
        ui_bootloader::{BootloaderLayoutType as _, BootloaderUI},
        ModelUI,
    },
    util::{from_c_array, from_c_str},
};

#[no_mangle]
extern "C" fn screen_attach(layout: *mut c_layout_t) -> u32 {
    // SAFETY: calling code is supposed to give us exclusive access to an already
    // initialized layout
    unsafe {
        let mut layout = LayoutBuffer::<<ModelUI as BootloaderUI>::CLayoutType>::new(layout);
        let layout = layout.get_mut();
        layout.show()
    }
}

#[no_mangle]
extern "C" fn screen_event(layout: *mut c_layout_t, signalled: &sysevents_t) -> u32 {
    let e = parse_event(signalled);
    // SAFETY: calling code is supposed to give us exclusive access to an already
    // initialized layout
    unsafe {
        let mut layout = LayoutBuffer::<<ModelUI as BootloaderUI>::CLayoutType>::new(layout);
        let layout = layout.get_mut();
        layout.event(e)
    }
}

#[no_mangle]
extern "C" fn screen_render(layout: *mut c_layout_t) {
    unsafe {
        let mut layout = LayoutBuffer::<<ModelUI as BootloaderUI>::CLayoutType>::new(layout);
        let layout = layout.get_mut();
        layout.render()
    }
}

#[no_mangle]
extern "C" fn screen_welcome(layout: *mut c_layout_t) {
    let screen = <ModelUI as BootloaderUI>::CLayoutType::init_welcome();
    // SAFETY: calling code is supposed to give us exclusive access to the layout
    let mut layout = unsafe { LayoutBuffer::new(layout) };
    layout.store(screen);
}

#[no_mangle]
extern "C" fn screen_install_success(
    restart_seconds: u8,
    initial_setup: bool,
    complete_draw: bool,
) {
    ModelUI::screen_install_success(restart_seconds, initial_setup, complete_draw);
}

#[no_mangle]
extern "C" fn screen_install_fail() {
    ModelUI::screen_install_fail();
}

#[no_mangle]
extern "C" fn screen_install_confirm(
    vendor_str: *const cty::c_char,
    vendor_str_len: u8,
    version: *const cty::c_char,
    fingerprint: *const cty::uint8_t,
    should_keep_seed: bool,
    is_newvendor: bool,
    is_newinstall: bool,
    version_cmp: cty::c_int,
) -> u32 {
    let text = unwrap!(unsafe { from_c_array(vendor_str, vendor_str_len as usize) });
    let version = unwrap!(unsafe { from_c_str(version) });

    let mut fingerprint_buffer: [u8; 64] = [0; 64];
    let fingerprint_str = unsafe {
        let fingerprint_slice = core::slice::from_raw_parts(fingerprint, 32);
        hexlify(fingerprint_slice, &mut fingerprint_buffer);
        core::str::from_utf8_unchecked(fingerprint_buffer.as_ref())
    };

    ModelUI::screen_install_confirm(
        text,
        version,
        fingerprint_str,
        should_keep_seed,
        is_newvendor,
        is_newinstall,
        version_cmp,
    )
}

#[no_mangle]
extern "C" fn screen_wipe_confirm() -> u32 {
    ModelUI::screen_wipe_confirm()
}

#[no_mangle]
extern "C" fn screen_unlock_bootloader_confirm() -> u32 {
    ModelUI::screen_unlock_bootloader_confirm()
}

#[no_mangle]
extern "C" fn screen_unlock_bootloader_success() {
    ModelUI::screen_unlock_bootloader_success();
}

#[no_mangle]
extern "C" fn screen_menu(initial_setup: bool, layout: *mut c_layout_t) {
    let screen = <ModelUI as BootloaderUI>::CLayoutType::init_menu(initial_setup);
    // SAFETY: calling code is supposed to give us exclusive access to the layout
    let mut layout = unsafe { LayoutBuffer::new(layout) };
    layout.store(screen);
}

#[no_mangle]
extern "C" fn screen_intro(
    bld_version: *const cty::c_char,
    vendor_str: *const cty::c_char,
    vendor_str_len: u8,
    version: *const cty::c_char,
    fw_ok: bool,
) -> u32 {
    let vendor = unwrap!(unsafe { from_c_array(vendor_str, vendor_str_len as usize) });
    let version = unwrap!(unsafe { from_c_str(version) });
    let bld_version = unwrap!(unsafe { from_c_str(bld_version) });

    ModelUI::screen_intro(bld_version, vendor, version, fw_ok)
}

#[no_mangle]
extern "C" fn screen_boot_stage_1(fading: bool) {
    ModelUI::screen_boot_stage_1(fading)
}

#[no_mangle]
extern "C" fn screen_boot_empty() {
    ModelUI::screen_boot_empty()
}

#[no_mangle]
extern "C" fn screen_boot(
    warning: bool,
    vendor_str: *const cty::c_char,
    vendor_str_len: usize,
    version: u32,
    vendor_img: *const cty::c_void,
    vendor_img_len: usize,
    wait: i32,
) {
    let vendor_str = unsafe { from_c_array(vendor_str, vendor_str_len) };
    let vendor_img =
        unsafe { core::slice::from_raw_parts(vendor_img as *const u8, vendor_img_len) };

    // Splits a version stored as a u32 into four numbers
    // starting with the major version.
    let version = version.to_le_bytes();

    ModelUI::screen_boot(warning, vendor_str, version, vendor_img, wait);
}

#[no_mangle]
extern "C" fn screen_wipe_progress(progress: u16, initialize: bool) {
    ModelUI::screen_wipe_progress(progress, initialize)
}

#[no_mangle]
extern "C" fn screen_install_progress(progress: u16, initialize: bool, initial_setup: bool) {
    ModelUI::screen_install_progress(progress, initialize, initial_setup)
}

#[no_mangle]
extern "C" fn screen_connect(initial_setup: bool, auto_update: bool, layout: *mut c_layout_t) {
    let screen = <ModelUI as BootloaderUI>::CLayoutType::init_connect(initial_setup, auto_update);
    // SAFETY: calling code is supposed to give us exclusive access to the layout
    let mut layout = unsafe { LayoutBuffer::new(layout) };
    layout.store(screen);
}

#[no_mangle]
extern "C" fn screen_wipe_success() {
    ModelUI::screen_wipe_success()
}

#[no_mangle]
extern "C" fn screen_wipe_fail() {
    ModelUI::screen_wipe_fail()
}

#[cfg(feature = "ble")]
#[no_mangle]
extern "C" fn screen_confirm_pairing(code: u32, initial_setup: bool) -> u32 {
    ModelUI::screen_confirm_pairing(code, initial_setup)
}

#[cfg(feature = "ble")]
#[no_mangle]
extern "C" fn screen_pairing_mode(
    initial_setup: bool,
    name: *const cty::c_char,
    name_len: usize,
    layout: *mut c_layout_t,
) {
    let name = unsafe { from_c_array(name, name_len).unwrap_or("") };
    let screen = <ModelUI as BootloaderUI>::CLayoutType::init_pairing_mode(initial_setup, name);
    // SAFETY: calling code is supposed to give us exclusive access to the layout
    let mut layout = unsafe { LayoutBuffer::new(layout) };
    layout.store(screen);
}

#[cfg(feature = "ble")]
#[no_mangle]
extern "C" fn screen_wireless_setup(
    name: *const cty::c_char,
    name_len: usize,
    layout: *mut c_layout_t,
) {
    let name = unsafe { from_c_array(name, name_len).unwrap_or("") };
    let screen = <ModelUI as BootloaderUI>::CLayoutType::init_wireless_setup(name);
    // SAFETY: calling code is supposed to give us exclusive access to the layout
    let mut layout = unsafe { LayoutBuffer::new(layout) };
    layout.store(screen);
}

#[cfg(feature = "ble")]
#[no_mangle]
extern "C" fn screen_pairing_mode_finalizing(initial_setup: bool) -> u32 {
    ModelUI::screen_pairing_mode_finalizing(initial_setup)
}

#[cfg(feature = "power_manager")]
#[no_mangle]
extern "C" fn screen_bootloader_entry_progress(progress: u16, initialize: bool) {
    ModelUI::screen_bootloader_entry_progress(progress, initialize)
}
