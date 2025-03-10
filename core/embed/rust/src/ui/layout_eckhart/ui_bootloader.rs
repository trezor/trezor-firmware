use crate::{
    trezorhal::secbool::{secbool, sectrue},
    ui::{
        component::Label,
        display::{self, toif::Toif, Color},
        geometry::{Alignment, Alignment2D, Offset, Point, Rect},
        layout::simplified::{run, show},
        shape::{self, render_on_display},
        ui_bootloader::BootloaderUI,
        CommonUI,
    },
};

use heapless::String;
use ufmt::uwrite;

use super::{
    bootloader::{
        BldActionBar, BldHeader, BldHeaderMsg, BldMenuScreen, BldTextScreen, BldWelcomeScreen,
    },
    component::{Button, WelcomeScreen},
    cshape::{render_loader, ScreenBorder},
    fonts,
    theme::{
        self, backlight,
        bootloader::{
            button_cancel, button_confirm, button_wipe_confirm, BLD_BG, BLD_FG,
            TEXT_FW_FINGERPRINT, TEXT_WARNING, WELCOME_COLOR,
        },
        button_default, BLUE, GREY, ICON_CHECKMARK, ICON_CLOSE, ICON_CROSS, RED, TEXT_NORMAL,
        TEXT_SMALL_GREY,
    },
    UIEckhart,
};

pub type BootloaderString = String<128>;

const RECONNECT_MESSAGE: &str = "Please reconnect\nthe device";

const SCREEN: Rect = UIEckhart::SCREEN;
// TODO: adjust offset
const PROGRESS_TEXT_ORIGIN: Point = SCREEN.top_left().ofs(Offset::new(24, 48));
const SCREEN_BORDER_BLUE: ScreenBorder = ScreenBorder::new(BLUE);
const SCREEN_BORDER_RED: ScreenBorder = ScreenBorder::new(RED);

impl UIEckhart {
    fn screen_progress(
        text: &str,
        progress: u16,
        initialize: bool,
        bg_color: Color,
        center_text: Option<&str>,
    ) {
        if initialize {
            Self::fadeout();
        }
        display::sync();

        render_on_display(None, Some(bg_color), |target| {
            shape::Text::new(PROGRESS_TEXT_ORIGIN, text, fonts::FONT_SATOSHI_REGULAR_38)
                .with_align(Alignment::Start)
                .with_fg(BLD_FG)
                .render(target);

            let border: &ScreenBorder = match bg_color {
                RED => &SCREEN_BORDER_RED,
                _ => &SCREEN_BORDER_BLUE,
            };
            render_loader(progress, border, target);

            if let Some(center_text) = center_text {
                shape::Text::new(SCREEN.center(), center_text, fonts::FONT_SATOSHI_REGULAR_38)
                    .with_align(Alignment::Center)
                    .with_fg(GREY)
                    .render(target);
            }
        });

        display::refresh();
        if initialize {
            Self::fadein();
        }
    }
}
impl BootloaderUI for UIEckhart {
    fn screen_welcome() {
        let mut frame = BldWelcomeScreen::new();
        show(&mut frame, true);
    }

    fn screen_install_success(restart_seconds: u8, initial_setup: bool, complete_draw: bool) {
        let mut reboot_msg = BootloaderString::new();

        let bg_color = if initial_setup { WELCOME_COLOR } else { BLD_BG };

        if restart_seconds >= 1 {
            // in practice, restart_seconds is 5 or less so this is fine
            let seconds_char = b'0' + restart_seconds % 10;
            unwrap!(reboot_msg.push(seconds_char as char));
            let progress = (5 - (restart_seconds as u16)).clamp(0, 5) * 200;

            Self::screen_progress(
                "Restarting device",
                progress,
                complete_draw,
                bg_color,
                Some(reboot_msg.as_str()),
            );
        } else {
            Self::screen_progress("Firmware installed", 1000, complete_draw, bg_color, None);
        }
    }

    fn screen_install_fail() {
        let mut screen = BldTextScreen::new(Label::new(
            "Firmware installation was not successful".into(),
            Alignment::Start,
            TEXT_NORMAL,
        ))
        .with_header(BldHeader::new_pay_attention())
        .with_footer(
            Label::centered(RECONNECT_MESSAGE.into(), TEXT_SMALL_GREY).vertically_centered(),
        )
        .with_screen_border(SCREEN_BORDER_BLUE);

        show(&mut screen, true);
    }

    fn screen_install_confirm(
        vendor: &str,
        version: &str,
        fingerprint: &str,
        should_keep_seed: bool,
        is_newvendor: bool,
        is_newinstall: bool,
        version_cmp: i32,
    ) -> u32 {
        let mut version_str: BootloaderString = String::new();
        unwrap!(version_str.push_str("Firmware version "));
        unwrap!(version_str.push_str(version));
        unwrap!(version_str.push_str("\nby "));
        unwrap!(version_str.push_str(vendor));

        let title_str = if is_newinstall {
            "Install firmware"
        } else if is_newvendor {
            "Change fw vendor"
        } else if version_cmp > 0 {
            "Update firmware"
        } else if version_cmp == 0 {
            "Reinstall firmware"
        } else {
            "Downgrade firmware"
        };
        let msg = Label::left_aligned(version_str.as_str().into(), TEXT_NORMAL);
        let alert = (!should_keep_seed).then_some(Label::left_aligned(
            "SEED WILL BE ERASED!".into(),
            TEXT_NORMAL,
        ));

        let header = BldHeader::new(title_str.into()).with_right_button(
            Button::with_icon(theme::ICON_INFO).styled(theme::button_default()),
            BldHeaderMsg::Info,
        );
        let (left, right) = if should_keep_seed {
            let l = Button::with_text("Cancel".into())
                .styled(button_cancel())
                .with_text_align(Alignment::Center);
            let r = Button::with_text("Install".into())
                .styled(button_confirm())
                .with_text_align(Alignment::Center);
            (l, r)
        } else {
            let l = Button::with_icon(ICON_CROSS)
                .styled(button_cancel())
                .with_text_align(Alignment::Center);
            let r = Button::with_icon(ICON_CHECKMARK)
                .styled(button_confirm())
                .with_text_align(Alignment::Center);
            (l, r)
        };

        let mut screen = BldTextScreen::new(msg)
            .with_header(header)
            .with_action_bar(BldActionBar::new_double(left, right))
            .with_screen_border(SCREEN_BORDER_BLUE)
            .with_more_info(
                BldHeader::new("FW Fingerprint".into())
                    .with_right_button(Button::with_icon(ICON_CLOSE), BldHeaderMsg::Cancelled),
                Label::left_aligned(fingerprint.into(), TEXT_FW_FINGERPRINT),
            );

        if let Some(alert) = alert {
            screen = screen.with_label2(alert);
        }

        run(&mut screen)
    }

    fn screen_wipe_confirm() -> u32 {
        let msg = Label::left_aligned(
            "Are you sure you want to factory reset the device?".into(),
            TEXT_NORMAL,
        );
        let alert = Label::left_aligned("SEED and FIRMWARE will be erased!".into(), TEXT_NORMAL);

        let right = Button::with_text("Reset".into()).styled(button_wipe_confirm());
        let left = Button::with_icon(theme::ICON_CHEVRON_LEFT).styled(button_default());

        let mut screen = BldTextScreen::new(msg)
            .with_label2(alert)
            .with_header(BldHeader::new_pay_attention())
            .with_action_bar(BldActionBar::new_double(left, right))
            .with_screen_border(SCREEN_BORDER_RED);

        run(&mut screen)
    }

    fn screen_unlock_bootloader_confirm() -> u32 {
        let msg1 =
            Label::left_aligned("Unlock bootloader".into(), TEXT_NORMAL).vertically_centered();
        let msg2 = Label::centered("This action cannot be undone!".into(), TEXT_NORMAL);

        let right = Button::with_text("Unlock".into()).styled(button_confirm());
        let left = Button::with_icon(theme::ICON_CHEVRON_LEFT).styled(button_cancel());

        let mut screen = BldTextScreen::new(msg1)
            .with_label2(msg2)
            .with_header(BldHeader::new_pay_attention())
            .with_action_bar(BldActionBar::new_double(left, right))
            .with_screen_border(SCREEN_BORDER_RED);

        run(&mut screen)
    }

    fn screen_unlock_bootloader_success() {
        let mut screen = BldTextScreen::new(Label::new(
            "Bootloader unlocked".into(),
            Alignment::Start,
            TEXT_NORMAL,
        ))
        .with_header(BldHeader::new_pay_attention())
        .with_footer(
            Label::centered(RECONNECT_MESSAGE.into(), TEXT_SMALL_GREY).vertically_centered(),
        )
        .with_screen_border(SCREEN_BORDER_BLUE);

        show(&mut screen, true);
    }

    fn screen_menu(firmware_present: secbool) -> u32 {
        run(&mut BldMenuScreen::new(firmware_present == sectrue))
    }

    fn screen_intro(bld_version: &str, vendor: &str, version: &str, fw_ok: bool) -> u32 {
        let mut title_str: BootloaderString = String::new();
        unwrap!(title_str.push_str("Bootloader "));
        unwrap!(title_str.push_str(bld_version));

        let mut version_str: BootloaderString = String::new();
        unwrap!(version_str.push_str("Firmware version\n"));
        unwrap!(version_str.push_str(version));
        unwrap!(version_str.push_str(" by "));
        unwrap!(version_str.push_str(vendor));

        let mut screen = BldTextScreen::new(Label::left_aligned(
            version_str.as_str().into(),
            TEXT_NORMAL,
        ))
        .with_header(BldHeader::new(title_str.as_str().into()).with_menu_button())
        .with_action_bar(BldActionBar::new_single(
            Button::with_text("Connect to host device".into()).styled(button_confirm()),
        ))
        .with_screen_border(SCREEN_BORDER_BLUE);

        if !fw_ok {
            screen = screen.with_label2(
                Label::new("FIRMWARE CORRUPTED".into(), Alignment::Start, TEXT_WARNING)
                    .vertically_centered(),
            );
        }

        run(&mut screen)
    }

    fn screen_boot_stage_1(fading: bool) {
        if fading {
            Self::fadeout();
        }

        let mut frame = WelcomeScreen::new();
        show(&mut frame, false);

        if fading {
            Self::fadein();
        } else {
            display::set_backlight(backlight::get_backlight_normal());
        }
    }

    fn screen_wipe_progress(progress: u16, initialize: bool) {
        Self::screen_progress("Resetting Trezor", progress, initialize, RED, None)
    }

    fn screen_install_progress(progress: u16, initialize: bool, _initial_setup: bool) {
        Self::screen_progress("Installing firmware", progress, initialize, BLD_BG, None)
    }

    fn screen_connect(_initial_setup: bool) {
        // NOTE: other layouts use a Connect component. Eckhart uses a BldTextScreen so
        // that the ScreenBorder can be shown and alignment can be adjusted.
        let mut screen = BldTextScreen::new(Label::left_aligned(
            "Waiting for host...".into(),
            TEXT_NORMAL,
        ))
        .with_screen_border(SCREEN_BORDER_BLUE);
        show(&mut screen, true);
    }

    fn screen_wipe_success() {
        let mut screen = BldTextScreen::new(Label::new(
            "Trezor reset successfully".into(),
            Alignment::Start,
            TEXT_NORMAL,
        ))
        .with_header(BldHeader::new("Done".into()).with_icon(theme::ICON_DONE, theme::GREY))
        .with_footer(
            Label::centered(RECONNECT_MESSAGE.into(), TEXT_SMALL_GREY).vertically_centered(),
        )
        .with_screen_border(SCREEN_BORDER_RED);

        show(&mut screen, true);
    }

    fn screen_wipe_fail() {
        let mut screen = BldTextScreen::new(Label::new(
            "Trezor reset was\nnot successful".into(),
            Alignment::Start,
            TEXT_NORMAL,
        ))
        .with_header(BldHeader::new_pay_attention())
        .with_footer(
            Label::centered(RECONNECT_MESSAGE.into(), TEXT_SMALL_GREY).vertically_centered(),
        )
        .with_screen_border(SCREEN_BORDER_RED);
        show(&mut screen, true);
    }

    fn screen_boot(
        warning: bool,
        vendor_str: Option<&str>,
        version: [u8; 4],
        vendor_img: &'static [u8],
        wait: i32,
    ) {
        let bg_color = if warning { RED } else { WELCOME_COLOR };

        display::sync();

        render_on_display(None, Some(bg_color), |target| {
            // Draw vendor image if it's valid and has size of 120x120
            if let Ok(toif) = Toif::new(vendor_img) {
                if (toif.width() == 120) && (toif.height() == 120) {
                    // Image position depends on the vendor string presence
                    let pos = if vendor_str.is_some() {
                        Point::new(SCREEN.width() / 2, 30)
                    } else {
                        Point::new(SCREEN.width() / 2, 60)
                    };

                    shape::ToifImage::new(pos, toif)
                        .with_align(Alignment2D::TOP_CENTER)
                        .with_fg(BLD_FG)
                        .render(target);
                }
            }

            // Draw vendor string if present
            if let Some(text) = vendor_str {
                let pos = Point::new(SCREEN.width() / 2, SCREEN.height() - 5 - 50);
                shape::Text::new(pos, text, fonts::FONT_SATOSHI_REGULAR_38)
                    .with_align(Alignment::Center)
                    .with_fg(BLD_FG) //COLOR_BL_BG
                    .render(target);

                let pos = Point::new(SCREEN.width() / 2, SCREEN.height() - 5 - 25);

                let mut version_text: BootloaderString = String::new();
                unwrap!(uwrite!(
                    version_text,
                    "{}.{}.{}",
                    version[0],
                    version[1],
                    version[2]
                ));

                shape::Text::new(pos, version_text.as_str(), fonts::FONT_SATOSHI_REGULAR_38)
                    .with_align(Alignment::Center)
                    .with_fg(BLD_FG)
                    .render(target);
            }

            // Draw a message
            match wait.cmp(&0) {
                core::cmp::Ordering::Equal => {}
                core::cmp::Ordering::Greater => {
                    let mut text: BootloaderString = String::new();
                    unwrap!(uwrite!(text, "starting in {} s", wait));

                    let pos = Point::new(SCREEN.width() / 2, SCREEN.height() - 5);
                    shape::Text::new(pos, text.as_str(), fonts::FONT_SATOSHI_REGULAR_38)
                        .with_align(Alignment::Center)
                        .with_fg(BLD_FG)
                        .render(target);
                }
                core::cmp::Ordering::Less => {
                    let pos = Point::new(SCREEN.width() / 2, SCREEN.height() - 5);
                    shape::Text::new(pos, "click to continue ...", fonts::FONT_SATOSHI_REGULAR_38)
                        .with_align(Alignment::Center)
                        .with_fg(BLD_FG)
                        .render(target);
                }
            }
        });

        display::refresh();
    }
}
