use heapless::String;

use crate::{
    strutil::hexlify,
    trezorhal::{io::io_button_read, secbool::secbool},
    ui::{
        component::{
            connect::Connect, Component, Event, EventCtx, Label, LineBreaking::BreakWordsNoHyphen,
            Never,
        },
        constant,
        constant::{HEIGHT, SCREEN},
        display::{self, Color, Font, Icon},
        event::ButtonEvent,
        geometry::{Alignment2D, Offset, Point, Rect},
        util::{from_c_array, from_c_str},
    },
};

use super::{
    component::{
        bl_confirm::{Confirm, ConfirmMsg},
        ResultScreen, WelcomeScreen,
    },
    theme::{
        bootloader::{BLD_BG, BLD_FG, ICON_ALERT, ICON_SPINNER, ICON_SUCCESS},
        ICON_ARM_LEFT, ICON_ARM_RIGHT, TEXT_BOLD, TEXT_NORMAL, WHITE,
    },
};

mod intro;
mod menu;
mod welcome;

use intro::Intro;
use menu::Menu;
use welcome::Welcome;

pub type BootloaderString = String<128>;

pub trait ReturnToC {
    fn return_to_c(self) -> u32;
}

impl ReturnToC for Never {
    fn return_to_c(self) -> u32 {
        unreachable!()
    }
}

impl ReturnToC for () {
    fn return_to_c(self) -> u32 {
        0
    }
}

impl ReturnToC for ConfirmMsg {
    fn return_to_c(self) -> u32 {
        self as u32
    }
}

fn button_eval() -> Option<ButtonEvent> {
    let event = io_button_read();
    if event == 0 {
        return None;
    }

    let event_type = event >> 24;
    let event_btn = event & 0xFFFFFF;

    let event = ButtonEvent::new(event_type, event_btn);

    if let Ok(event) = event {
        return Some(event);
    }
    None
}

fn run<F>(frame: &mut F) -> u32
where
    F: Component,
    F::Msg: ReturnToC,
{
    frame.place(SCREEN);
    frame.paint();
    display::refresh();

    while button_eval().is_some() {}

    loop {
        let event = button_eval();
        if let Some(e) = event {
            let mut ctx = EventCtx::new();
            let msg = frame.event(&mut ctx, Event::Button(e));

            if let Some(message) = msg {
                return message.return_to_c();
            }

            frame.paint();
            display::refresh();
        }
    }
}

fn show<F>(frame: &mut F)
where
    F: Component,
{
    frame.place(SCREEN);
    display::sync();
    frame.paint();
    display::refresh();
}

#[no_mangle]
extern "C" fn screen_install_confirm(
    vendor_str: *const cty::c_char,
    vendor_str_len: u8,
    version: *const cty::c_char,
    fingerprint: *const cty::uint8_t,
    should_keep_seed: bool,
    is_newvendor: bool,
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

    let mut version_str: BootloaderString = String::new();
    unwrap!(version_str.push_str("Firmware version "));
    unwrap!(version_str.push_str(version));
    unwrap!(version_str.push_str("\nby "));
    unwrap!(version_str.push_str(text));

    let title_str = if is_newvendor {
        "CHANGE FW VENDOR"
    } else if version_cmp > 0 {
        "UPDATE FIRMWARE"
    } else if version_cmp == 0 {
        "REINSTALL FW"
    } else {
        "DOWNGRADE FW"
    };

    let message = Label::left_aligned(version_str.as_str(), TEXT_NORMAL).vertically_centered();
    let fingerprint = Label::left_aligned(
        fingerprint_str,
        TEXT_NORMAL.with_line_breaking(BreakWordsNoHyphen),
    )
    .vertically_centered();

    let alert =
        (!should_keep_seed).then_some(Label::left_aligned("Seed will be erased!", TEXT_NORMAL));

    let mut frame = Confirm::new(BLD_BG, title_str, message, alert, "INSTALL", false)
        .with_info_screen("FW FINGERPRINT", fingerprint);
    run(&mut frame)
}

#[no_mangle]
extern "C" fn screen_wipe_confirm() -> u32 {
    let message =
        Label::left_aligned("Seed and firmware will be erased!", TEXT_NORMAL).vertically_centered();

    let mut frame = Confirm::new(BLD_BG, "FACTORY RESET", message, None, "RESET", false);

    run(&mut frame)
}

#[no_mangle]
extern "C" fn screen_unlock_bootloader_confirm() -> u32 {
    let message =
        Label::left_aligned("This action cannot be undone!", TEXT_NORMAL).vertically_centered();

    let mut frame = Confirm::new(BLD_BG, "UNLOCK BOOTLOADER?", message, None, "UNLOCK", true);

    run(&mut frame)
}

#[no_mangle]
extern "C" fn screen_unlock_bootloader_success() {
    let title = Label::centered("Bootloader unlocked", TEXT_BOLD).vertically_centered();

    let content =
        Label::centered("Please reconnect the\ndevice", TEXT_NORMAL).vertically_centered();

    let mut frame = ResultScreen::new(BLD_FG, BLD_BG, ICON_SPINNER, title, content, true);
    show(&mut frame);
}

#[no_mangle]
extern "C" fn screen_menu(firmware_present: secbool) -> u32 {
    run(&mut Menu::new(firmware_present))
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

    let mut title_str: BootloaderString = String::new();
    unwrap!(title_str.push_str("BOOTLOADER "));
    unwrap!(title_str.push_str(bld_version));

    let mut version_str: BootloaderString = String::new();
    unwrap!(version_str.push_str("Firmware version "));
    unwrap!(version_str.push_str(version));
    unwrap!(version_str.push_str("\nby "));
    unwrap!(version_str.push_str(vendor));

    let mut frame = Intro::new(title_str.as_str(), version_str.as_str(), fw_ok);
    run(&mut frame)
}

fn screen_progress(
    text: &str,
    text2: &str,
    progress: u16,
    initialize: bool,
    fg_color: Color,
    bg_color: Color,
    icon: Option<(Icon, Color)>,
) {
    if initialize {
        display::rect_fill(SCREEN, bg_color);
    }

    let progress = if progress < 20 { 20 } else { progress };

    display::rect_rounded2_partial(
        Rect::new(
            SCREEN.top_center() + Offset::new(-9, 3),
            SCREEN.top_center() + Offset::new(9, 18 + 3),
        ),
        fg_color,
        bg_color,
        ((100_u32 * progress as u32) / 1000) as _,
        icon,
    );
    display::text_center(
        SCREEN.center() + Offset::y(8),
        text,
        Font::BOLD,
        fg_color,
        bg_color,
    );
    display::text_center(
        SCREEN.center() + Offset::y(20),
        text2,
        Font::BOLD,
        fg_color,
        bg_color,
    );

    display::refresh();
}

#[no_mangle]
extern "C" fn screen_install_progress(progress: u16, initialize: bool, _initial_setup: bool) {
    screen_progress(
        "Installing",
        "firmware",
        progress,
        initialize,
        BLD_FG,
        BLD_BG,
        Some((ICON_SUCCESS, BLD_FG)),
    );
}

#[no_mangle]
extern "C" fn screen_wipe_progress(progress: u16, initialize: bool) {
    screen_progress(
        "Resetting",
        "Trezor",
        progress,
        initialize,
        BLD_FG,
        BLD_BG,
        Some((ICON_SUCCESS, BLD_FG)),
    );
}

#[no_mangle]
extern "C" fn screen_connect(_initial_setup: bool) {
    let mut frame = Connect::new("Waiting for host...", BLD_FG, BLD_BG);
    show(&mut frame);
}

#[no_mangle]
extern "C" fn screen_wipe_success() {
    let title = Label::centered("Trezor Reset", TEXT_BOLD).vertically_centered();

    let content =
        Label::centered("Please reconnect\nthe device", TEXT_NORMAL).vertically_centered();

    let mut frame = ResultScreen::new(BLD_FG, BLD_BG, ICON_SPINNER, title, content, true);
    show(&mut frame);
}

#[no_mangle]
extern "C" fn screen_wipe_fail() {
    let title = Label::centered("Reset failed", TEXT_BOLD).vertically_centered();

    let content =
        Label::centered("Please reconnect\nthe device", TEXT_NORMAL).vertically_centered();

    let mut frame = ResultScreen::new(BLD_FG, BLD_BG, ICON_ALERT, title, content, true);
    show(&mut frame);
}

#[no_mangle]
extern "C" fn screen_boot_empty(_fading: bool) {
    display::rect_fill(SCREEN, BLD_BG);

    let mut frame = WelcomeScreen::new(true);
    show(&mut frame);
}

#[no_mangle]
extern "C" fn screen_install_fail() {
    let title = Label::centered("Install failed", TEXT_BOLD).vertically_centered();

    let content =
        Label::centered("Please reconnect\nthe device", TEXT_NORMAL).vertically_centered();

    let mut frame = ResultScreen::new(BLD_FG, BLD_BG, ICON_ALERT, title, content, true);
    show(&mut frame);
}

#[no_mangle]
extern "C" fn screen_install_success(
    restart_seconds: u8,
    _initial_setup: bool,
    complete_draw: bool,
) {
    let mut reboot_msg = BootloaderString::new();

    if restart_seconds >= 1 {
        unwrap!(reboot_msg.push_str("Restarting in "));
        // in practice, restart_seconds is 5 or less so this is fine
        let seconds_char = b'0' + restart_seconds % 10;
        unwrap!(reboot_msg.push(seconds_char as char));
    } else {
        unwrap!(reboot_msg.push_str("Reconnect the device"));
    }

    let title = Label::centered("Firmware installed", TEXT_BOLD).vertically_centered();

    let content = Label::centered(reboot_msg.as_str(), TEXT_NORMAL).vertically_centered();

    let mut frame = ResultScreen::new(BLD_FG, BLD_BG, ICON_SPINNER, title, content, complete_draw);
    show(&mut frame);
}

#[no_mangle]
extern "C" fn screen_welcome() {
    let mut frame = Welcome::new();
    show(&mut frame);
}

#[no_mangle]
extern "C" fn bld_continue_label(bg_color: cty::uint16_t) {
    display::text_center(
        Point::new(constant::WIDTH / 2, HEIGHT - 2),
        "CONTINUE",
        Font::NORMAL,
        WHITE,
        Color::from_u16(bg_color),
    );
    ICON_ARM_LEFT.draw(
        Point::new(constant::WIDTH / 2 - 36, HEIGHT - 6),
        Alignment2D::TOP_LEFT,
        WHITE,
        Color::from_u16(bg_color),
    );
    ICON_ARM_RIGHT.draw(
        Point::new(constant::WIDTH / 2 + 25, HEIGHT - 6),
        Alignment2D::TOP_LEFT,
        WHITE,
        Color::from_u16(bg_color),
    );
}
