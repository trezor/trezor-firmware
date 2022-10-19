use crate::{
    trezorhal::io::io_button_read,
    ui::{
        component::{Component, Never},
        display::{self, Font},
        geometry::Point,
        model_tr::constant,
    },
};

mod confirm;
mod intro;
mod menu;
mod theme;
mod title;

use crate::ui::{
    component::{
        text::paragraphs::{Paragraph, ParagraphVecShort, Paragraphs, VecExt},
        Event, EventCtx,
    },
    constant::{screen, BACKLIGHT_NORMAL, WIDTH},
    display::{fade_backlight_duration, Color, TextOverlay},
    event::ButtonEvent,
    geometry::{LinearPlacement, Offset, Rect},
    model_tr::{
        bootloader::{
            confirm::Confirm,
            intro::Intro,
            menu::Menu,
            theme::{bld_button_cancel, bld_button_default, BLD_BG, BLD_FG},
        },
        component::{Button, ButtonPos, ResultScreen},
        theme::LOGO_EMPTY,
    },
    util::{from_c_array, from_c_str},
};

const SCREEN_ADJ: Rect = screen().split_top(64).0;

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
    frame.place(SCREEN_ADJ);
    frame.paint();
    fade_backlight_duration(BACKLIGHT_NORMAL as _, 500);

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
        }
    }
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

    const ICON: Option<&'static [u8]> = None; //Some(RECEIVE);

    let msg = if downgrade {
        "Downgrade firmware by"
    } else if vendor {
        "Change vendor to"
    } else {
        "Update firmware by"
    };

    let mut message = ParagraphVecShort::new();

    message.add(Paragraph::new(&theme::TEXT_NORMAL, msg).centered());
    message.add(Paragraph::new(&theme::TEXT_NORMAL, text).centered());
    message.add(Paragraph::new(&theme::TEXT_NORMAL, version).centered());

    if vendor || downgrade {
        message.add(Paragraph::new(&theme::TEXT_BOLD, "Seed will be erased!").centered());
    }

    let left = Button::with_text(ButtonPos::Left, "CANCEL", bld_button_cancel());
    let right = Button::with_text(ButtonPos::Right, "INSTALL", bld_button_default());

    let mut frame = Confirm::new(
        BLD_BG,
        ICON,
        Paragraphs::new(message).with_placement(LinearPlacement::vertical().align_at_center()),
        left,
        right,
        false,
    );

    run(&mut frame)
}

#[no_mangle]
extern "C" fn screen_wipe_confirm() -> u32 {
    const ICON: Option<&'static [u8]> = None; //Some(ERASE_BIG);

    let mut messages = ParagraphVecShort::new();

    messages.add(
        Paragraph::new(
            &theme::TEXT_NORMAL,
            "Do you really want to wipe the device?",
        )
        .centered(),
    );
    messages.add(Paragraph::new(&theme::TEXT_BOLD, "Seed will be erased!").centered());

    let message =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let left = Button::with_text(ButtonPos::Left, "WIPE", bld_button_default());
    let right = Button::with_text(ButtonPos::Right, "CANCEL", bld_button_cancel());

    let mut frame = Confirm::new(BLD_BG, ICON, message, left, right, true);

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

    run(&mut Intro::new(bld_version, vendor, version))
}

fn screen_progress(
    text: &str,
    progress: u16,
    initialize: bool,
    fg_color: Color,
    bg_color: Color,
    _icon: Option<(&[u8], Color)>,
) -> u32 {
    if initialize {
        display::rect_fill(constant::screen(), bg_color);
    }

    let loader_area = Rect::new(Point::new(5, 24), Point::new(WIDTH - 5, 24 + 16));

    let mut text = TextOverlay::new(text, Font::NORMAL);
    text.place(loader_area.center() + Offset::y(Font::NORMAL.text_height() / 2));

    let fill_to = (loader_area.width() as u32 * progress as u32) / 1000;

    display::bar_with_text_and_fill(loader_area, Some(text), fg_color, bg_color, 0, fill_to as _);

    // display::text_center(
    //     Point::new(constant::WIDTH / 2, 100),
    //     text,
    //     Font::NORMAL,
    //     fg_color,
    //     bg_color,
    // );
    // display::loader(progress, -20, fg_color, bg_color, icon);
    0
}

const INITIAL_INSTALL_LOADER_COLOR: Color = Color::rgb(0x4A, 0x90, 0xE2);

#[no_mangle]
extern "C" fn screen_install_progress(
    progress: u16,
    initialize: bool,
    _initial_setup: bool,
) -> u32 {
    screen_progress(
        "INSTALLING FIRMWARE",
        progress,
        initialize,
        BLD_FG,
        BLD_BG,
        None, //Some((theme::RECEIVE, fg_color)),
    )
}

#[no_mangle]
extern "C" fn screen_wipe_progress(progress: u16, initialize: bool) -> u32 {
    screen_progress(
        "WIPING DEVICE",
        progress,
        initialize,
        theme::BLD_FG,
        BLD_BG,
        None, //Some((theme::ERASE_BIG, theme::BLD_FG)),
    )
}

#[no_mangle]
extern "C" fn screen_connect() -> u32 {
    let mut messages = ParagraphVecShort::new();

    messages.add(Paragraph::new(&theme::TEXT_NORMAL, "Waiting for host...").centered());

    let mut frame =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    frame.place(SCREEN_ADJ);
    frame.paint();
    0
}

#[no_mangle]
extern "C" fn screen_wipe_success() -> u32 {
    let mut messages = ParagraphVecShort::new();
    messages.add(Paragraph::new(&theme::TEXT_NORMAL, "Device wiped").centered());
    messages.add(Paragraph::new(&theme::TEXT_NORMAL, "successfully.").centered());

    let m_top =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut messages = ParagraphVecShort::new();
    messages.add(Paragraph::new(&theme::TEXT_NORMAL, "PLEASE RECONNECT").centered());
    messages.add(Paragraph::new(&theme::TEXT_NORMAL, "THE DEVICE").centered());

    let m_bottom =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut frame = ResultScreen::new(BLD_FG, BLD_BG, m_top, m_bottom, true);
    frame.place(SCREEN_ADJ);
    frame.paint();
    0
}

#[no_mangle]
extern "C" fn screen_wipe_fail() -> u32 {
    let mut messages = ParagraphVecShort::new();
    messages.add(Paragraph::new(&theme::TEXT_NORMAL, "Device wipe was").centered());
    messages.add(Paragraph::new(&theme::TEXT_NORMAL, "not successful.").centered());

    let m_top =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut messages = ParagraphVecShort::new();
    messages.add(Paragraph::new(&theme::TEXT_NORMAL, "PLEASE RECONNECT").centered());
    messages.add(Paragraph::new(&theme::TEXT_NORMAL, "THE DEVICE").centered());

    let m_bottom =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut frame = ResultScreen::new(BLD_FG, BLD_BG, m_top, m_bottom, true);
    frame.place(SCREEN_ADJ);
    frame.paint();
    0
}

#[no_mangle]
extern "C" fn screen_boot_empty(_firmware_present: bool) {
    display::icon(SCREEN_ADJ.center(), LOGO_EMPTY, BLD_FG, BLD_BG);
}

#[no_mangle]
extern "C" fn screen_install_fail() -> u32 {
    let mut messages = ParagraphVecShort::new();
    messages.add(Paragraph::new(&theme::TEXT_NORMAL, "Firmware installation was").centered());
    messages.add(Paragraph::new(&theme::TEXT_NORMAL, "not successful.").centered());
    let m_top =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut messages = ParagraphVecShort::new();
    messages.add(Paragraph::new(&theme::TEXT_NORMAL, "PLEASE RECONNECT").centered());
    messages.add(Paragraph::new(&theme::TEXT_NORMAL, "THE DEVICE").centered());

    let m_bottom =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut frame = ResultScreen::new(BLD_FG, BLD_BG, m_top, m_bottom, true);
    frame.place(SCREEN_ADJ);
    frame.paint();
    0
}

fn screen_install_success_bld(msg: &'static str, complete_draw: bool) -> u32 {
    let mut messages = ParagraphVecShort::new();
    messages.add(Paragraph::new(&theme::TEXT_NORMAL, "Firmware installed").centered());
    messages.add(Paragraph::new(&theme::TEXT_NORMAL, "successfully.").centered());

    let m_top =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut messages = ParagraphVecShort::new();
    messages.add(Paragraph::new(&theme::TEXT_NORMAL, msg).centered());

    let m_bottom =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut frame = ResultScreen::new(BLD_FG, BLD_BG, m_top, m_bottom, complete_draw);
    frame.place(SCREEN_ADJ);
    frame.paint();
    0
}

fn screen_install_success_initial(msg: &'static str, complete_draw: bool) -> u32 {
    let mut messages = ParagraphVecShort::new();
    messages.add(Paragraph::new(&theme::TEXT_NORMAL, "Firmware installed").centered());
    messages.add(Paragraph::new(&theme::TEXT_NORMAL, "successfully.").centered());

    let m_top =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut messages = ParagraphVecShort::new();
    messages.add(Paragraph::new(&theme::TEXT_NORMAL, msg).centered());

    let m_bottom =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut frame = ResultScreen::new(BLD_FG, BLD_BG, m_top, m_bottom, complete_draw);
    frame.place(SCREEN_ADJ);
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
    messages.add(Paragraph::new(&theme::TEXT_BOLD, "Get started with").centered());
    messages.add(Paragraph::new(&theme::TEXT_BOLD, "your trezor at").centered());
    messages.add(Paragraph::new(&theme::TEXT_BOLD, "trezor.io/start").centered());
    let mut frame =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    frame.place(SCREEN_ADJ);
    frame.paint();
    0
}
