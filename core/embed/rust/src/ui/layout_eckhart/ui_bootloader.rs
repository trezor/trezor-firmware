use crate::{
    bootloader::run,
    ui::{
        component::{base::Component, text::TextStyle, Label},
        display::{self, toif::Toif, Color},
        geometry::{Alignment, Alignment2D, Offset, Point, Rect},
        layout::simplified::show,
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
        ConnectScreen, WirelessSetupScreen,
    },
    component::{render_logo, Button},
    cshape::{render_loader, ScreenBorder},
    fonts::{FONT_SATOSHI_MEDIUM_26, FONT_SATOSHI_REGULAR_38},
    theme::{
        self,
        bootloader::{
            button_cancel, button_confirm, button_default, button_wipe_confirm, BLD_BG, BLD_FG,
            TEXT_FW_FINGERPRINT, TEXT_WARNING, WELCOME_COLOR,
        },
        BLACK, BLUE, GREEN_LIGHT, GREY, ICON_CHECKMARK, ICON_CROSS, RED, TEXT_NORMAL,
        TEXT_SMALL_GREY, WHITE,
    },
    UIEckhart, CANCEL_MESSAGE, WAIT_FOR_RESTART_MESSAGE, WAIT_MESSAGE,
};

#[cfg(feature = "ble")]
use super::bootloader::{ConfirmPairingScreen, PairingFinalizationScreen, PairingModeScreen};

pub type BootloaderString = String<128>;

const RESTART_MESSAGE: &str = "Restart";

const SCREEN: Rect = UIEckhart::SCREEN;
const PROGRESS_WAIT_HEIGHT: i16 = 70;
const PROGRESS_WAIT_ORIGIN: Point = SCREEN
    .bottom_left()
    .ofs(Offset::new(0, -PROGRESS_WAIT_HEIGHT));

const SCREEN_BORDER_BLUE: ScreenBorder = ScreenBorder::new(BLUE);
const SCREEN_BORDER_RED: ScreenBorder = ScreenBorder::new(RED);
const SCREEN_BORDER_GREEN_LIGHT: ScreenBorder = ScreenBorder::new(GREEN_LIGHT);

impl UIEckhart {
    fn screen_progress(
        text: &str,
        wait_msg: &str,
        initialize: bool,
        loader_progress: u16,
        border: &ScreenBorder,
    ) {
        if initialize {
            Self::fadeout();
        }
        display::sync();

        let mut label = Label::left_aligned(text.into(), TEXT_NORMAL);
        let mut wait_msg = Label::centered(wait_msg.into(), TEXT_SMALL_GREY).vertically_centered();
        render_on_display(None, Some(BLD_BG), |target| {
            render_loader(loader_progress, border, target);

            label.place(Rect::from_top_left_and_size(
                theme::PROGRESS_TEXT_ORIGIN,
                Offset::new(
                    SCREEN.width() - 2 * theme::PADDING,
                    4 * FONT_SATOSHI_REGULAR_38.text_height(),
                ),
            ));
            label.render(target);

            wait_msg.place(Rect::from_top_left_and_size(
                PROGRESS_WAIT_ORIGIN,
                Offset::new(SCREEN.width(), PROGRESS_WAIT_HEIGHT),
            ));
            wait_msg.render(target);
        });

        display::refresh();
        if initialize {
            Self::fadein();
        }
    }
}

impl BootloaderUI for UIEckhart {
    fn screen_welcome() -> (u32, u32) {
        let mut screen = BldWelcomeScreen::new();
        run(&mut screen, false, true)
    }

    fn screen_menu(initial_setup: bool, communication: bool) -> (u32, u32) {
        let mut screen = BldMenuScreen::new();
        if !initial_setup {
            screen = screen.with_screen_border(SCREEN_BORDER_BLUE);
        }
        run(&mut screen, true, communication)
    }

    fn screen_connect(initial_setup: bool, show_menu: bool) -> (u32, u32) {
        let mut screen = ConnectScreen::new(initial_setup);
        if show_menu {
            screen = screen.with_header(BldHeader::new("Bootloader".into()).with_menu_button());
        }
        if !initial_setup {
            screen = screen.with_screen_border(SCREEN_BORDER_BLUE);
        }
        run(&mut screen, true, true)
    }

    #[cfg(feature = "ble")]
    fn screen_pairing_mode(initial_setup: bool, name: &'static str) -> (u32, u32) {
        let mut screen = PairingModeScreen::new(name.into());
        if !initial_setup {
            screen = screen.with_screen_border(SCREEN_BORDER_BLUE);
        }
        run(&mut screen, true, false)
    }

    #[cfg(feature = "ble")]
    fn screen_wireless_setup(name: &'static str) -> (u32, u32) {
        let mut screen = WirelessSetupScreen::new(name.into());
        run(&mut screen, true, true)
    }

    fn screen_install_success(restart_seconds: u8, initial_setup: bool, complete_draw: bool) {
        let header_color = if initial_setup { GREEN_LIGHT } else { GREY };
        let mut screen = BldTextScreen::new(Label::new(
            "Firmware installed successfully.".into(),
            Alignment::Start,
            TEXT_NORMAL,
        ))
        .with_header(BldHeader::new_done(header_color));

        let mut reboot_msg = BootloaderString::new();
        if restart_seconds >= 1 {
            let seconds_char = b'0' + restart_seconds % 10;
            unwrap!(reboot_msg.push_str("Restarting in "));
            unwrap!(reboot_msg.push(seconds_char as char));
            screen = screen.with_footer(
                Label::centered(reboot_msg.as_str().into(), TEXT_SMALL_GREY).vertically_centered(),
            );
        }

        if !initial_setup {
            screen = screen.with_screen_border(SCREEN_BORDER_BLUE);
        }

        show(&mut screen, complete_draw);
    }

    fn screen_install_fail() {
        let mut screen = BldTextScreen::new(Label::new(
            "Firmware installation was not successful.".into(),
            Alignment::Start,
            TEXT_NORMAL,
        ))
        .with_header(BldHeader::new_important())
        .with_footer(
            Label::centered(WAIT_FOR_RESTART_MESSAGE.into(), TEXT_SMALL_GREY).vertically_centered(),
        )
        .with_screen_border(SCREEN_BORDER_RED);

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
            Button::with_icon(theme::ICON_INFO).styled(theme::bootloader::button_header()),
            BldHeaderMsg::Info,
        );
        let (left, right) = if should_keep_seed {
            let l = Button::with_text(CANCEL_MESSAGE.into())
                .styled(button_cancel())
                .with_text_align(Alignment::Center);
            let r = Button::with_text("Install".into())
                .styled(button_confirm())
                .with_text_align(Alignment::Center);
            (l, r)
        } else {
            let l = Button::with_icon(ICON_CROSS).styled(button_cancel());
            let r = Button::with_icon(ICON_CHECKMARK);
            (l, r)
        };

        let mut screen = BldTextScreen::new(msg)
            .with_header(header)
            .with_action_bar(BldActionBar::new_double(left, right))
            .with_screen_border(SCREEN_BORDER_BLUE)
            .with_more_info(
                BldHeader::new("FW Fingerprint".into()).with_close_button(),
                Label::left_aligned(fingerprint.into(), TEXT_FW_FINGERPRINT),
            );

        if let Some(alert) = alert {
            screen = screen.with_secondary_text(alert);
        }

        let (_, res) = run(&mut screen, true, false);
        res
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
            .with_secondary_text(alert)
            .with_header(BldHeader::new_important())
            .with_action_bar(BldActionBar::new_double(left, right))
            .with_screen_border(SCREEN_BORDER_RED);

        let (_, res) = run(&mut screen, true, false);
        res
    }

    fn screen_unlock_bootloader_confirm() -> u32 {
        let msg1 =
            Label::left_aligned("Unlock bootloader".into(), TEXT_NORMAL).vertically_centered();
        let msg2 = Label::left_aligned(
            "Your seed will be erased. Unlocking bootloader is irreversible.".into(),
            TEXT_NORMAL,
        );

        let right = Button::with_text("Unlock".into()).styled(button_wipe_confirm());
        let left = Button::with_icon(theme::ICON_CHEVRON_LEFT).styled(button_cancel());

        let mut screen = BldTextScreen::new(msg1)
            .with_secondary_text(msg2)
            .with_header(BldHeader::new_important())
            .with_action_bar(BldActionBar::new_double(left, right))
            .with_screen_border(SCREEN_BORDER_RED);

        let (_, res) = run(&mut screen, true, false);
        res
    }

    fn screen_unlock_bootloader_success() {
        let mut screen = BldTextScreen::new(Label::new(
            "Bootloader unlocked".into(),
            Alignment::Start,
            TEXT_NORMAL,
        ))
        .with_header(BldHeader::new_done(GREY))
        .with_action_bar(BldActionBar::new_single(
            Button::with_text(RESTART_MESSAGE.into()).styled(button_cancel()),
        ))
        .with_screen_border(SCREEN_BORDER_RED);

        run(&mut screen, true, false);
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
            Button::with_text("Initiate connection".into()).styled(button_confirm()),
        ))
        .with_screen_border(SCREEN_BORDER_BLUE);

        if !fw_ok {
            screen = screen.with_secondary_text(
                Label::new("FIRMWARE CORRUPTED".into(), Alignment::Start, TEXT_WARNING)
                    .vertically_centered(),
            );
        }

        let (_, res) = run(&mut screen, true, false);
        res
    }

    fn screen_boot_stage_1(_fading: bool) {}

    fn screen_boot_empty() {
        render_on_display(None, Some(BLACK), |target| {
            render_logo(target);
        });

        display::refresh();
        Self::fadein();
    }

    fn screen_wipe_progress(progress: u16, initialize: bool) {
        Self::screen_progress(
            "Resetting Trezor",
            WAIT_MESSAGE,
            initialize,
            progress,
            &SCREEN_BORDER_RED,
        )
    }

    fn screen_install_progress(
        progress: u16,
        initialize: bool,
        initial_setup: bool,
        wireless: bool,
    ) {
        let border = if initial_setup {
            &SCREEN_BORDER_GREEN_LIGHT
        } else {
            &SCREEN_BORDER_BLUE
        };

        let msg = if wireless {
            "Keep your Trezor close to\nthe connected device"
        } else {
            "Do not disconnect\nyour Trezor"
        };

        Self::screen_progress("Installing\nfirmware...", msg, initialize, progress, border)
    }

    fn screen_wipe_success() {
        let mut screen = BldTextScreen::new(Label::new(
            "Trezor reset successfully".into(),
            Alignment::Start,
            TEXT_NORMAL,
        ))
        .with_header(BldHeader::new_done(GREY))
        .with_action_bar(BldActionBar::new_single(
            Button::with_text(RESTART_MESSAGE.into()).styled(button_default()),
        ))
        .with_screen_border(SCREEN_BORDER_RED);

        run(&mut screen, true, false);
    }

    fn screen_wipe_fail() {
        let mut screen = BldTextScreen::new(Label::new(
            "Trezor reset was\nnot successful".into(),
            Alignment::Start,
            TEXT_NORMAL,
        ))
        .with_header(BldHeader::new_important())
        .with_footer(
            Label::centered(WAIT_FOR_RESTART_MESSAGE.into(), TEXT_SMALL_GREY).vertically_centered(),
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
        let bg_color = if warning {
            Color::rgb(0xFF, 0, 0)
        } else {
            WELCOME_COLOR
        };

        display::sync();

        let pos = Point::new(0, 200);

        let label_text = vendor_str.unwrap_or("");

        const TEXT_WHITE: TextStyle =
            TextStyle::new(FONT_SATOSHI_REGULAR_38, WHITE, BLACK, WHITE, WHITE);

        let mut label = Label::new(label_text.into(), Alignment::Center, TEXT_WHITE);
        label.place(Rect::from_top_left_and_size(
            pos,
            Offset::new(SCREEN.width(), label.text_height(SCREEN.width())),
        ));

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
            if vendor_str.is_some() {
                label.render(target);

                let pos = Point::new(SCREEN.width() / 2, 350);

                let mut version_text: BootloaderString = String::new();
                unwrap!(uwrite!(
                    version_text,
                    "{}.{}.{}",
                    version[0],
                    version[1],
                    version[2]
                ));

                shape::Text::new(pos, version_text.as_str(), FONT_SATOSHI_REGULAR_38)
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

                    let pos = Point::new(SCREEN.width() / 2, SCREEN.height() - 40);
                    shape::Text::new(pos, text.as_str(), FONT_SATOSHI_MEDIUM_26)
                        .with_align(Alignment::Center)
                        .with_fg(BLD_FG)
                        .render(target);
                }
                core::cmp::Ordering::Less => {
                    let pos = Point::new(SCREEN.width() / 2, SCREEN.height() - 40);
                    shape::Text::new(pos, "Tap to continue", FONT_SATOSHI_MEDIUM_26)
                        .with_align(Alignment::Center)
                        .with_fg(BLD_FG)
                        .render(target);
                }
            }
        });

        display::refresh();
    }

    #[cfg(feature = "ble")]
    fn screen_confirm_pairing(code: u32, initial_setup: bool) -> u32 {
        let mut screen = ConfirmPairingScreen::new(code);
        if !initial_setup {
            screen = screen.with_screen_border(SCREEN_BORDER_BLUE);
        }
        let (_, res) = run(&mut screen, true, false);
        res
    }

    #[cfg(feature = "ble")]
    fn screen_pairing_mode_finalizing(initial_setup: bool) -> u32 {
        let mut screen = PairingFinalizationScreen::new(initial_setup);
        if !initial_setup {
            screen = screen.with_screen_border(SCREEN_BORDER_BLUE);
        }
        let (_, res) = run(&mut screen, true, false);
        res
    }

    #[cfg(feature = "power_manager")]
    fn screen_bootloader_entry_progress(progress: u16, initialize: bool) {
        Self::screen_progress(
            "Starting\nbootloader...",
            "Release the button",
            initialize,
            progress,
            &SCREEN_BORDER_BLUE,
        )
    }
}
