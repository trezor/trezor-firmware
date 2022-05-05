use crate::{
    trezorhal::io::io_touch_read,
    ui::{
        component::{Component, Event, EventCtx, Never},
        display::{self, Font},
        event::TouchEvent,
        geometry::Point,
        model_tt::constant,
    },
};
use heapless::String;
use num_traits::ToPrimitive;

pub mod confirm;
mod connect;
pub mod intro;
pub mod menu;
pub mod theme;

use crate::{
    strutil::hexlify,
    ui::{
        component::text::paragraphs::{Paragraph, ParagraphVecShort, Paragraphs, VecExt},
        constant::screen,
        display::{Color, Icon},
        geometry::{LinearPlacement, CENTER},
        model_tt::{
            bootloader::{
                connect::Connect,
                theme::{
                    button_install_cancel, button_install_confirm, button_wipe_cancel,
                    button_wipe_confirm, BLD_BG, BLD_FG, BLD_WIPE_COLOR, ERASE_BIG, LOGO_EMPTY,
                    RECEIVE, TEXT_WIPE_BOLD, WELCOME_COLOR,
                },
            },
            component::{Button, ResultScreen},
            theme::{
                BACKLIGHT_DIM, BACKLIGHT_NORMAL, BG, BLACK, FG, GREY_DARK, ICON_SUCCESS_SMALL,
                ICON_WARN_SMALL, TEXT_ERROR_BOLD, TEXT_ERROR_NORMAL, WHITE,
            },
        },
        util::{from_c_array, from_c_str},
    },
};
use confirm::Confirm;
use intro::Intro;
use menu::Menu;

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
    display::fade_backlight_duration(BACKLIGHT_NORMAL, 500);
}

fn fadeout() {
    display::fade_backlight_duration(BACKLIGHT_DIM, 500);
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
    downgrade: bool,
    vendor: bool,
) -> u32 {
    let text = unwrap!(unsafe { from_c_array(vendor_str, vendor_str_len as usize) });
    let version = unwrap!(unsafe { from_c_str(version) });

    let mut fingerprint_buffer: [u8; 64] = [0; 64];
    let fingerprint_str = unsafe {
        let fingerprint_slice = core::slice::from_raw_parts(fingerprint as *const u8, 32);
        hexlify(fingerprint_slice, &mut fingerprint_buffer);
        core::str::from_utf8_unchecked(fingerprint_buffer.as_ref())
    };

    let mut version_str: String<64> = String::new();
    unwrap!(version_str.push_str("Firmware version "));
    unwrap!(version_str.push_str(version));

    let mut vendor_str: String<64> = String::new();
    unwrap!(vendor_str.push_str("by "));
    unwrap!(vendor_str.push_str(text));

    let title = if downgrade {
        "DOWNGRADE FW"
    } else if vendor {
        "CHANGE FW VENDOR"
    } else {
        "UPDATE FIRMWARE"
    };

    let mut messages = ParagraphVecShort::new();

    messages.add(Paragraph::new(&theme::TEXT_NORMAL, version_str.as_ref()));
    messages.add(Paragraph::new(&theme::TEXT_NORMAL, vendor_str.as_ref()));

    if vendor || downgrade {
        messages
            .add(Paragraph::new(&theme::TEXT_BOLD, "Seed will be erased!").with_top_padding(16));
    }

    let message =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut messages = ParagraphVecShort::new();
    messages.add(Paragraph::new(&theme::TEXT_FINGERPRINT, fingerprint_str));

    let fingerprint =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let left = Button::with_text("CANCEL").styled(button_install_cancel());
    let right = Button::with_text("INSTALL").styled(button_install_confirm());

    let mut frame = Confirm::new(
        BLD_BG,
        None,
        left,
        right,
        false,
        (Some(title), message),
        Some(("FW FINGERPRINT", fingerprint)),
    );

    run(&mut frame)
}

#[no_mangle]
extern "C" fn screen_wipe_confirm() -> u32 {
    let icon = Some(Icon::new(ERASE_BIG));

    let mut messages = ParagraphVecShort::new();

    messages.add(
        Paragraph::new(
            &TEXT_ERROR_NORMAL,
            "Are you sure you want to factory reset the device?",
        )
        .centered(),
    );
    messages.add(Paragraph::new(&TEXT_ERROR_BOLD, "Seed and firmware\nwill be erased!").centered());

    let message =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let left = Button::with_text("RESET").styled(button_wipe_confirm());
    let right = Button::with_text("CANCEL").styled(button_wipe_cancel());

    let mut frame = Confirm::new(
        BLD_WIPE_COLOR,
        icon,
        left,
        right,
        true,
        (None, message),
        None,
    );

    run(&mut frame)
}

#[no_mangle]
extern "C" fn screen_menu(bld_version: *const cty::c_char) -> u32 {
    let bld_version = unwrap!(unsafe { from_c_str(bld_version) });

    run(&mut Menu::new(bld_version))
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

    let mut fw: String<64> = String::new();
    unwrap!(fw.push_str("Firmware "));
    unwrap!(fw.push_str(version));

    let mut vendor_: String<64> = String::new();
    unwrap!(vendor_.push_str("by "));
    unwrap!(vendor_.push_str(vendor));

    let mut messages = ParagraphVecShort::new();

    messages.add(Paragraph::new(&theme::TEXT_NORMAL, fw.as_ref()));
    messages.add(Paragraph::new(&theme::TEXT_NORMAL, vendor_.as_ref()));

    let p = Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_start());

    let mut frame = Intro::new(bld_version, p);

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
        Point::new(constant::WIDTH / 2, 214),
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
    let bg_color = if initial_setup { WELCOME_COLOR } else { BG };
    let fg_color = if initial_setup { FG } else { BLD_FG };

    screen_progress(
        "Installing firmware...",
        progress,
        initialize,
        fg_color,
        bg_color,
        Some((Icon::new(RECEIVE), fg_color)),
    )
}

#[no_mangle]
extern "C" fn screen_wipe_progress(progress: u16, initialize: bool) {
    screen_progress(
        "Resetting Trezor...",
        progress,
        initialize,
        theme::BLD_FG,
        BLD_WIPE_COLOR,
        Some((Icon::new(ERASE_BIG), theme::BLD_FG)),
    )
}

#[no_mangle]
extern "C" fn screen_connect() {
    let mut frame = Connect::new("Waiting for host...");
    show(&mut frame, true);
}

#[no_mangle]
extern "C" fn screen_wipe_success() {
    let mut messages = ParagraphVecShort::new();

    messages.add(Paragraph::new(&TEXT_ERROR_BOLD, "Trezor reset").centered());
    messages.add(Paragraph::new(&TEXT_ERROR_BOLD, "successfully.").centered());

    let m_top =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut messages = ParagraphVecShort::new();
    messages.add(Paragraph::new(&TEXT_WIPE_BOLD, "PLEASE RECONNECT").centered());
    messages.add(Paragraph::new(&TEXT_WIPE_BOLD, "THE DEVICE").centered());

    let m_bottom =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut frame = ResultScreen::new(
        WHITE,
        BLD_WIPE_COLOR,
        Icon::new(ICON_SUCCESS_SMALL),
        m_top,
        m_bottom,
        true,
    );
    show(&mut frame, true);
}

#[no_mangle]
extern "C" fn screen_wipe_fail() {
    let mut messages = ParagraphVecShort::new();

    messages.add(Paragraph::new(&TEXT_ERROR_BOLD, "Trezor reset was").centered());
    messages.add(Paragraph::new(&TEXT_ERROR_BOLD, "not successful.").centered());
    let m_top =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut messages = ParagraphVecShort::new();

    messages.add(Paragraph::new(&TEXT_WIPE_BOLD, "PLEASE RECONNECT").centered());
    messages.add(Paragraph::new(&TEXT_WIPE_BOLD, "THE DEVICE").centered());
    let m_bottom =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut frame = ResultScreen::new(
        WHITE,
        BLD_WIPE_COLOR,
        Icon::new(ICON_WARN_SMALL),
        m_top,
        m_bottom,
        true,
    );
    show(&mut frame, true);
}

#[no_mangle]
extern "C" fn screen_boot_empty(firmware_present: bool, fading: bool) {
    if fading {
        fadeout();
    }

    let fg = if firmware_present { GREY_DARK } else { WHITE };
    let bg = if firmware_present {
        BLACK
    } else {
        WELCOME_COLOR
    };
    display::rect_fill(constant::screen(), bg);
    let icon = Icon::new(LOGO_EMPTY);
    icon.draw(screen().center(), CENTER, fg, bg);

    if fading {
        fadein();
    } else {
        display::set_backlight(BACKLIGHT_NORMAL);
    }
}

#[no_mangle]
extern "C" fn screen_install_fail() {
    let mut messages = ParagraphVecShort::new();
    messages.add(Paragraph::new(&theme::TEXT_BOLD, "Firmware installation was").centered());
    messages.add(Paragraph::new(&theme::TEXT_BOLD, "not successful.").centered());

    let m_top =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut messages = ParagraphVecShort::new();
    messages.add(Paragraph::new(&theme::TEXT_SUBMSG, "PLEASE RECONNECT").centered());
    messages.add(Paragraph::new(&theme::TEXT_SUBMSG, "THE DEVICE").centered());
    let m_bottom =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut frame = ResultScreen::new(
        WHITE,
        BLD_BG,
        Icon::new(ICON_WARN_SMALL),
        m_top,
        m_bottom,
        true,
    );
    show(&mut frame, true);
}

fn screen_install_success_bld(msg: &'static str, complete_draw: bool) {
    let mut messages = ParagraphVecShort::new();
    messages.add(Paragraph::new(&theme::TEXT_BOLD, "Firmware installed").centered());
    messages.add(Paragraph::new(&theme::TEXT_BOLD, "successfully.").centered());
    let m_top =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut messages = ParagraphVecShort::new();
    messages.add(Paragraph::new(&theme::TEXT_SUBMSG, msg).centered());
    let m_bottom =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut frame = ResultScreen::new(
        WHITE,
        BLD_BG,
        Icon::new(ICON_SUCCESS_SMALL),
        m_top,
        m_bottom,
        complete_draw,
    );
    show(&mut frame, complete_draw);
}

fn screen_install_success_initial(msg: &'static str, complete_draw: bool) {
    let mut messages = ParagraphVecShort::new();
    messages.add(Paragraph::new(&theme::TEXT_WELCOME_BOLD, "Firmware installed").centered());
    messages.add(Paragraph::new(&theme::TEXT_WELCOME_BOLD, "successfully.").centered());

    let m_top =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut messages = ParagraphVecShort::new();
    messages.add(Paragraph::new(&theme::TEXT_SUBMSG_INITIAL, msg).centered());

    let m_bottom =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut frame = ResultScreen::new(
        FG,
        WELCOME_COLOR,
        Icon::new(ICON_SUCCESS_SMALL),
        m_top,
        m_bottom,
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
}

#[no_mangle]
extern "C" fn screen_welcome() {
    fadeout();
    display::rect_fill(screen(), WELCOME_COLOR);

    let mut messages = ParagraphVecShort::new();
    messages.add(Paragraph::new(&theme::TEXT_WELCOME, "Get started with").centered());
    messages.add(Paragraph::new(&theme::TEXT_WELCOME, "your trezor at").centered());
    messages.add(
        Paragraph::new(&theme::TEXT_WELCOME_BOLD, "trezor.io/start")
            .centered()
            .with_top_padding(2),
    );
    let mut frame =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());
    show(&mut frame, false);
    fadein();
}
