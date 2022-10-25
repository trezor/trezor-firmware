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

pub mod confirm;
mod connect;
mod fwinfo;
pub mod intro;
pub mod menu;
pub mod theme;
mod title;

use crate::ui::{
    component::text::paragraphs::{Paragraph, ParagraphVecShort, Paragraphs, VecExt},
    constant::screen,
    display::Color,
    geometry::LinearPlacement,
    model_tt::{
        bootloader::{
            connect::Connect,
            theme::{
                button_install_cancel, button_install_confirm, button_wipe_cancel,
                button_wipe_confirm, BLD_BG, BLD_FG, BLD_WIPE_COLOR, ERASE_BIG, LOGO_EMPTY,
                RECEIVE, WELCOME_COLOR,
            },
        },
        component::{Button, ResultScreen},
        theme::{
            BACKLIGHT_DIM, BACKLIGHT_NORMAL, BG, BLACK, FG, GREY_DARK, ICON_SUCCESS_SMALL,
            ICON_WARN_SMALL, TEXT_ERROR_BOLD, TEXT_ERROR_NORMAL, WHITE,
        },
    },
    util::{from_c_array, from_c_str},
};
use confirm::Confirm;
use fwinfo::FwInfo;
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

impl ReturnToC for () {
    fn return_to_c(self) -> u32 {
        0
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
            frame.paint();
        }
    }
}

fn touch_eval() -> Option<TouchEvent> {
    let event = io_touch_read();
    if event == 0 {
        return None;
    }
    let event_type = event >> 24;
    let ex = ((event >> 12) & 0xFFF) as i16;
    let ey = (event & 0xFFF) as i16;

    let event = TouchEvent::new(event_type, ex as _, ey as _);

    if let Ok(event) = event {
        return Some(event);
    }
    None
}

#[no_mangle]
extern "C" fn screen_install_confirm(
    vendor_str: *const cty::c_char,
    vendor_str_len: u8,
    version: *const cty::c_char,
    downgrade: bool,
    vendor: bool,
) -> u32 {
    let text = unwrap!(unsafe { from_c_array(vendor_str, vendor_str_len as usize) });
    let version = unwrap!(unsafe { from_c_str(version) });

    const ICON: Option<&'static [u8]> = Some(RECEIVE);

    let msg = if downgrade {
        "Downgrade firmware by"
    } else if vendor {
        "Change vendor to"
    } else {
        "Update firmware by"
    };

    let mut messages = ParagraphVecShort::new();

    messages.add(Paragraph::new(&theme::TEXT_NORMAL, msg));
    messages.add(Paragraph::new(&theme::TEXT_NORMAL, text));
    messages.add(Paragraph::new(&theme::TEXT_NORMAL, version));

    if vendor || downgrade {
        messages.add(Paragraph::new(&theme::TEXT_BOLD, "Seed will be erased!").centered());
    }

    let message =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let left = Button::with_text("CANCEL").styled(button_install_cancel());
    let right = Button::with_text("INSTALL").styled(button_install_confirm());

    let mut frame = Confirm::new(BLD_BG, ICON, message, left, right, false);

    run(&mut frame)
}

#[no_mangle]
extern "C" fn screen_wipe_confirm() -> u32 {
    const ICON: Option<&'static [u8]> = Some(ERASE_BIG);

    let mut messages = ParagraphVecShort::new();

    messages.add(
        Paragraph::new(&TEXT_ERROR_NORMAL, "Do you really want to wipe the device?").centered(),
    );
    messages.add(Paragraph::new(&TEXT_ERROR_BOLD, "Seed will be erased!").centered());

    let message =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let left = Button::with_text("WIPE").styled(button_wipe_confirm());
    let right = Button::with_text("CANCEL").styled(button_wipe_cancel());

    let mut frame = Confirm::new(BLD_WIPE_COLOR, ICON, message, left, right, true);

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
    display::set_backlight(0);
    let vendor = unwrap!(unsafe { from_c_array(vendor_str, vendor_str_len as usize) });
    let version = unwrap!(unsafe { from_c_str(version) });
    let bld_version = unwrap!(unsafe { from_c_str(bld_version) });

    run(&mut Intro::new(bld_version, vendor, version))
}

fn screen_progress(
    text: &str,
    progress: u16,
    initialize: bool,
    fg_color: Color,
    bg_color: Color,
    icon: Option<(&[u8], Color)>,
) -> u32 {
    if initialize {
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
    0
}

#[no_mangle]
extern "C" fn screen_install_progress(progress: u16, initialize: bool, initial_setup: bool) -> u32 {
    let bg_color = if initial_setup { WELCOME_COLOR } else { BG };
    let fg_color = if initial_setup { FG } else { BLD_FG };

    screen_progress(
        "Installing firmware...",
        progress,
        initialize,
        fg_color,
        bg_color,
        Some((theme::RECEIVE, fg_color)),
    )
}

#[no_mangle]
extern "C" fn screen_wipe_progress(progress: u16, initialize: bool) -> u32 {
    screen_progress(
        "Wiping device...",
        progress,
        initialize,
        theme::BLD_FG,
        BLD_WIPE_COLOR,
        Some((theme::ERASE_BIG, theme::BLD_FG)),
    )
}

#[no_mangle]
extern "C" fn screen_connect() -> u32 {
    let mut frame = Connect::new("Waiting for host...");

    frame.place(constant::screen());
    frame.paint();
    0
}

#[no_mangle]
extern "C" fn screen_fwinfo(fingerprint: *const cty::c_char) -> u32 {
    let fingerprint = unwrap!(unsafe { from_c_str(fingerprint) });

    run(&mut FwInfo::new(fingerprint))
}
//
// fn screen_result(message_top: &'static str, message_bottom: &'static str,
// icon: &'static [u8], bg: Color) -> u32 {
//
//     let m_top = Paragraphs::new()
//         .add(
//             theme::TEXT_BOLD,message_top,
//         ).centered()
//         .with_placement(LinearPlacement::vertical().align_at_center());
//
//     let m_bottom = Paragraphs::new()
//         .add(
//             theme::TEXT_SUBMSG,message_bottom,
//         ).centered()
//         .with_placement(LinearPlacement::vertical().align_at_center());
//
//     let mut frame = Result::new(bg, icon, m_top, m_bottom);
//     frame.place(constant::screen());
//     frame.paint();
//     0
// }

#[no_mangle]
extern "C" fn screen_wipe_success() -> u32 {
    let mut messages = ParagraphVecShort::new();

    messages.add(Paragraph::new(&theme::TEXT_BOLD, "Device wiped").centered());
    messages.add(Paragraph::new(&theme::TEXT_BOLD, "successfully.").centered());

    let m_top =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut messages = ParagraphVecShort::new();
    messages.add(Paragraph::new(&theme::TEXT_SUBMSG, "PLEASE RECONNECT").centered());
    messages.add(Paragraph::new(&theme::TEXT_SUBMSG, "THE DEVICE").centered());

    let m_bottom =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut frame = ResultScreen::new(WHITE, BLD_BG, ICON_SUCCESS_SMALL, m_top, m_bottom, true);
    frame.place(constant::screen());
    frame.paint();
    0
}

#[no_mangle]
extern "C" fn screen_wipe_fail() -> u32 {
    let mut messages = ParagraphVecShort::new();

    messages.add(Paragraph::new(&theme::TEXT_BOLD, "Device wipe was").centered());
    messages.add(Paragraph::new(&theme::TEXT_BOLD, "not successful.").centered());
    let m_top =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut messages = ParagraphVecShort::new();

    messages.add(Paragraph::new(&theme::TEXT_SUBMSG, "PLEASE RECONNECT").centered());
    messages.add(Paragraph::new(&theme::TEXT_SUBMSG, "THE DEVICE").centered());
    let m_bottom =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut frame = ResultScreen::new(WHITE, BLD_BG, ICON_WARN_SMALL, m_top, m_bottom, true);
    frame.place(constant::screen());
    frame.paint();
    0
}

#[no_mangle]
extern "C" fn screen_boot_empty(firmware_present: bool) {
    let fg = if firmware_present { GREY_DARK } else { WHITE };
    let bg = if firmware_present {
        BLACK
    } else {
        WELCOME_COLOR
    };
    display::rect_fill(constant::screen(), bg);
    display::icon(constant::screen().center(), LOGO_EMPTY, fg, bg);
}

#[no_mangle]
extern "C" fn screen_install_fail() -> u32 {
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

    let mut frame = ResultScreen::new(WHITE, BLD_BG, ICON_WARN_SMALL, m_top, m_bottom, true);
    frame.place(constant::screen());
    frame.paint();
    0
}

fn screen_install_success_bld(msg: &'static str, complete_draw: bool) -> u32 {
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
        ICON_SUCCESS_SMALL,
        m_top,
        m_bottom,
        complete_draw,
    );
    frame.place(constant::screen());
    frame.paint();
    0
}

fn screen_install_success_initial(msg: &'static str, complete_draw: bool) -> u32 {
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
        ICON_SUCCESS_SMALL,
        m_top,
        m_bottom,
        complete_draw,
    );
    frame.place(constant::screen());
    frame.paint();
    0
}

#[no_mangle]
extern "C" fn screen_install_success(
    reboot_msg: *const cty::c_char,
    initial_setup: bool,
    complete_draw: bool,
) -> u32 {
    let msg = unwrap!(unsafe { from_c_str(reboot_msg) });
    if initial_setup {
        screen_install_success_initial(msg, complete_draw)
    } else {
        screen_install_success_bld(msg, complete_draw)
    }
}

#[no_mangle]
extern "C" fn screen_welcome() -> u32 {
    let mut messages = ParagraphVecShort::new();
    display::rect_fill(screen(), WELCOME_COLOR);
    messages.add(Paragraph::new(&theme::TEXT_WELCOME, "Get started with").centered());
    messages.add(Paragraph::new(&theme::TEXT_WELCOME, "your trezor at").centered());
    messages.add(Paragraph::new(&theme::TEXT_WELCOME_BOLD, "trezor.io/start").centered());
    let mut frame =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    frame.place(constant::screen());
    frame.paint();
    0
}
