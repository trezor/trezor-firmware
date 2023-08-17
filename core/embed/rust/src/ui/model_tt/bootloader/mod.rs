use crate::{
    strutil::hexlify,
    trezorhal::io::io_touch_read,
    ui::{
        component::{Component, Event, EventCtx, Label, Never},
        constant::{screen, HEIGHT},
        display::{self, Color, Font, Icon},
        event::TouchEvent,
        geometry::Point,
        model_tt::{
            bootloader::{
                confirm::ConfirmTitle,
                connect::Connect,
                theme::{
                    button_bld, button_confirm, button_wipe_cancel, button_wipe_confirm, BLD_BG,
                    BLD_FG, BLD_WIPE_COLOR, CHECK24, CHECK40, DOWNLOAD32, FIRE32, FIRE40,
                    TEXT_WIPE_BOLD, TEXT_WIPE_NORMAL, WARNING40, WELCOME_COLOR, X24,
                },
                welcome::Welcome,
            },
            component::{Button, ResultScreen, WelcomeScreen},
            constant,
            theme::{BACKLIGHT_DIM, BACKLIGHT_NORMAL, FG, WHITE},
        },
        util::{from_c_array, from_c_str},
    },
};
use heapless::String;
use num_traits::ToPrimitive;

pub mod confirm;
mod connect;
pub mod intro;
pub mod menu;
pub mod theme;
pub mod welcome;

use crate::ui::model_tt::theme::BLACK;
use confirm::Confirm;
use intro::Intro;
use menu::Menu;

use self::theme::{RESULT_FW_INSTALL, RESULT_INITIAL, RESULT_WIPE};

pub type BootloaderString = String<128>;

const RECONNECT_MESSAGE: &str = "PLEASE RECONNECT\nTHE DEVICE";

pub trait ReturnToC {
    fn return_to_c(self) -> u32;
}

impl ReturnToC for Never {
    fn return_to_c(self) -> u32 {
        unreachable!()
    }
}

impl<T> ReturnToC for T
where
    T: ToPrimitive,
{
    fn return_to_c(self) -> u32 {
        self.to_u32().unwrap()
    }
}

fn fadein() {
    display::fade_backlight_duration(BACKLIGHT_NORMAL, 150);
}

fn fadeout() {
    display::fade_backlight_duration(BACKLIGHT_DIM, 150);
}

fn run<F>(frame: &mut F) -> u32
where
    F: Component,
    F::Msg: ReturnToC,
{
    frame.place(constant::screen());
    fadeout();
    display::sync();
    frame.paint();
    fadein();

    loop {
        let event = touch_eval();
        if let Some(e) = event {
            let mut ctx = EventCtx::new();
            let msg = frame.event(&mut ctx, Event::Touch(e));

            if let Some(message) = msg {
                return message.return_to_c();
            }
            display::sync();
            frame.paint();
            display::refresh();
        }
    }
}

fn show<F>(frame: &mut F, fading: bool)
where
    F: Component,
{
    frame.place(screen());
    if fading {
        fadeout()
    };
    display::sync();
    frame.paint();
    display::refresh();
    if fading {
        fadein()
    };
}

fn touch_eval() -> Option<TouchEvent> {
    let event = io_touch_read();
    if event == 0 {
        return None;
    }
    let event_type = event >> 24;
    let ex = ((event >> 12) & 0xFFF) as i16;
    let ey = (event & 0xFFF) as i16;

    TouchEvent::new(event_type, ex as _, ey as _).ok()
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
        let fingerprint_slice = core::slice::from_raw_parts(fingerprint as *const u8, 32);
        hexlify(fingerprint_slice, &mut fingerprint_buffer);
        core::str::from_utf8_unchecked(fingerprint_buffer.as_ref())
    };

    let mut version_str: BootloaderString = String::new();
    unwrap!(version_str.push_str("Firmware version "));
    unwrap!(version_str.push_str(version));
    unwrap!(version_str.push_str("\nby "));
    unwrap!(version_str.push_str(text));

    let title_str = if is_newvendor {
        "CHANGE FW\nVENDOR"
    } else if version_cmp > 0 {
        "UPDATE FIRMWARE"
    } else if version_cmp == 0 {
        "REINSTALL FW"
    } else {
        "DOWNGRADE FW"
    };
    let title = Label::left_aligned(title_str, theme::TEXT_BOLD).vertically_centered();
    let msg = Label::left_aligned(version_str.as_ref(), theme::TEXT_NORMAL);
    let alert = (!should_keep_seed).then_some(Label::left_aligned(
        "SEED WILL BE ERASED!",
        theme::TEXT_BOLD,
    ));

    let (left, right) = if should_keep_seed {
        let l = Button::with_text("CANCEL").styled(button_bld());
        let r = Button::with_text("INSTALL").styled(button_confirm());
        (l, r)
    } else {
        let l = Button::with_icon(Icon::new(X24)).styled(button_bld());
        let r = Button::with_icon(Icon::new(CHECK24)).styled(button_confirm());
        (l, r)
    };

    let mut frame = Confirm::new(
        BLD_BG,
        left,
        right,
        ConfirmTitle::Text(title),
        msg,
        alert,
        Some(("FW FINGERPRINT", fingerprint_str)),
    );

    run(&mut frame)
}

#[no_mangle]
extern "C" fn screen_wipe_confirm() -> u32 {
    let icon = Icon::new(FIRE40);

    let msg = Label::centered(
        "Are you sure you want to factory reset the device?",
        TEXT_WIPE_NORMAL,
    );
    let alert = Label::centered("SEED AND FIRMWARE\nWILL BE ERASED!", TEXT_WIPE_BOLD);

    let right = Button::with_text("RESET").styled(button_wipe_confirm());
    let left = Button::with_text("CANCEL").styled(button_wipe_cancel());

    let mut frame = Confirm::new(
        BLD_WIPE_COLOR,
        left,
        right,
        ConfirmTitle::Icon(icon),
        msg,
        Some(alert),
        None,
    );

    run(&mut frame)
}

#[no_mangle]
extern "C" fn screen_menu() -> u32 {
    run(&mut Menu::new())
}

#[no_mangle]
extern "C" fn screen_intro(
    bld_version: *const cty::c_char,
    vendor_str: *const cty::c_char,
    vendor_str_len: u8,
    version: *const cty::c_char,
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

    let mut frame = Intro::new(title_str.as_str(), version_str.as_str());

    run(&mut frame)
}

fn screen_progress(
    text: &str,
    progress: u16,
    initialize: bool,
    fg_color: Color,
    bg_color: Color,
    icon: Option<(Icon, Color)>,
) {
    if initialize {
        fadeout();
        display::rect_fill(constant::screen(), bg_color);
    }

    display::text_center(
        Point::new(constant::WIDTH / 2, HEIGHT - 45),
        text,
        Font::NORMAL,
        fg_color,
        bg_color,
    );
    display::loader(progress, -20, fg_color, bg_color, icon);
    if initialize {
        fadein();
    }
}

#[no_mangle]
extern "C" fn screen_install_progress(progress: u16, initialize: bool, initial_setup: bool) {
    let bg_color = if initial_setup { WELCOME_COLOR } else { BLD_BG };
    let fg_color = if initial_setup { FG } else { BLD_FG };

    screen_progress(
        "Installing firmware",
        progress,
        initialize,
        fg_color,
        bg_color,
        Some((Icon::new(DOWNLOAD32), fg_color)),
    )
}

#[no_mangle]
extern "C" fn screen_wipe_progress(progress: u16, initialize: bool) {
    screen_progress(
        "Resetting Trezor",
        progress,
        initialize,
        theme::BLD_FG,
        BLD_WIPE_COLOR,
        Some((Icon::new(FIRE32), theme::BLD_FG)),
    )
}

#[no_mangle]
extern "C" fn screen_connect() {
    let mut frame = Connect::new("Waiting for host...");
    show(&mut frame, true);
}

#[no_mangle]
extern "C" fn screen_wipe_success() {
    let mut frame = ResultScreen::new(
        &RESULT_WIPE,
        Icon::new(CHECK40),
        "Trezor reset\nsuccessfully",
        RECONNECT_MESSAGE,
        true,
    );
    show(&mut frame, true);
}

#[no_mangle]
extern "C" fn screen_wipe_fail() {
    let mut frame = ResultScreen::new(
        &RESULT_WIPE,
        Icon::new(WARNING40),
        "Trezor reset was\nnot successful",
        RECONNECT_MESSAGE,
        true,
    );
    show(&mut frame, true);
}

#[no_mangle]
extern "C" fn screen_boot_empty(fading: bool) {
    if fading {
        fadeout();
    }

    display::rect_fill(constant::screen(), BLACK);

    let mut frame = WelcomeScreen::new(true);
    show(&mut frame, false);

    if fading {
        fadein();
    } else {
        display::set_backlight(BACKLIGHT_NORMAL);
    }
}

#[no_mangle]
extern "C" fn screen_install_fail() {
    let mut frame = ResultScreen::new(
        &RESULT_FW_INSTALL,
        Icon::new(WARNING40),
        "Firmware installation was not successful",
        RECONNECT_MESSAGE,
        true,
    );
    show(&mut frame, true);
}

fn screen_install_success_bld(msg: &'static str, complete_draw: bool) {
    let mut frame = ResultScreen::new(
        &RESULT_FW_INSTALL,
        Icon::new(CHECK40),
        "Firmware installed\nsuccessfully",
        msg,
        complete_draw,
    );
    show(&mut frame, complete_draw);
}

fn screen_install_success_initial(msg: &'static str, complete_draw: bool) {
    let mut frame = ResultScreen::new(
        &RESULT_INITIAL,
        Icon::new(CHECK40),
        "Firmware installed\nsuccessfully",
        msg,
        complete_draw,
    );
    show(&mut frame, complete_draw);
}

#[no_mangle]
extern "C" fn screen_install_success(
    reboot_msg: *const cty::c_char,
    initial_setup: bool,
    complete_draw: bool,
) {
    let msg = unwrap!(unsafe { from_c_str(reboot_msg) });
    if initial_setup {
        screen_install_success_initial(msg, complete_draw)
    } else {
        screen_install_success_bld(msg, complete_draw)
    }
    display::refresh();
}

#[no_mangle]
extern "C" fn screen_welcome_model() {
    let mut frame = WelcomeScreen::new(false);
    show(&mut frame, false);
}

#[no_mangle]
extern "C" fn screen_welcome() {
    let mut frame = Welcome::new();
    show(&mut frame, true);
}

#[no_mangle]
extern "C" fn bld_continue_label(bg_color: cty::uint16_t) {
    display::text_center(
        Point::new(constant::WIDTH / 2, HEIGHT - 5),
        "click to continue ...",
        Font::NORMAL,
        WHITE,
        Color::from_u16(bg_color),
    );
}
