use heapless::String;

use crate::{
    trezorhal::secbool::secbool,
    ui::{
        component::{connect::Connect, Label, LineBreaking::BreakWordsNoHyphen},
        constant,
        constant::{HEIGHT, SCREEN},
        display::{self, Color, Icon},
        geometry::{Alignment2D, Offset, Point},
        layout::simplified::{run, show, ReturnToC},
    },
};

use super::{
    component::{
        bl_confirm::{Confirm, ConfirmMsg},
        ResultScreen, WelcomeScreen,
    },
    cshape, fonts,
    theme::{
        bootloader::{BLD_BG, BLD_FG, ICON_ALERT, ICON_SPINNER, ICON_SUCCESS},
        ICON_ARM_LEFT, ICON_ARM_RIGHT, TEXT_BOLD, TEXT_NORMAL,
    },
    UICaesar,
};

use crate::ui::{display::toif::Toif, geometry::Alignment, shape, shape::render_on_display};

use ufmt::uwrite;

mod intro;
mod menu;
mod welcome;

use crate::ui::ui_bootloader::BootloaderUI;
use intro::Intro;
use menu::Menu;
use welcome::Welcome;

pub type BootloaderString = String<128>;

impl ReturnToC for ConfirmMsg {
    fn return_to_c(self) -> u32 {
        self as u32
    }
}

impl UICaesar {
    fn screen_progress(
        text: &str,
        text2: &str,
        progress: u16,
        _initialize: bool,
        fg_color: Color,
        bg_color: Color,
        icon: Option<(Icon, Color)>,
    ) {
        let progress = if progress < 20 { 20 } else { progress };

        display::sync();

        render_on_display(None, Some(bg_color), |target| {
            let center = SCREEN.top_center() + Offset::y(12);

            cshape::LoaderCircular::new(center, progress)
                .with_color(fg_color)
                .render(target);

            if let Some((icon, color)) = icon {
                shape::ToifImage::new(center, icon.toif)
                    .with_align(Alignment2D::CENTER)
                    .with_fg(color)
                    .render(target);
            }

            shape::Text::new(SCREEN.center() + Offset::y(8), text, fonts::FONT_BOLD)
                .with_align(Alignment::Center)
                .with_fg(fg_color)
                .render(target);

            shape::Text::new(SCREEN.center() + Offset::y(20), text2, fonts::FONT_BOLD)
                .with_align(Alignment::Center)
                .with_fg(fg_color)
                .render(target);
        });

        display::refresh();
    }
}

impl BootloaderUI for UICaesar {
    fn screen_welcome() {
        let mut frame = Welcome::new();
        show(&mut frame, true);
    }

    fn screen_install_success(restart_seconds: u8, _initial_setup: bool, complete_draw: bool) {
        let mut reboot_msg = BootloaderString::new();

        if restart_seconds >= 1 {
            unwrap!(reboot_msg.push_str("Restarting in "));
            // in practice, restart_seconds is 5 or less so this is fine
            let seconds_char = b'0' + restart_seconds % 10;
            unwrap!(reboot_msg.push(seconds_char as char));
        } else {
            unwrap!(reboot_msg.push_str("Reconnect the device"));
        }

        let title = Label::centered("Firmware installed".into(), TEXT_BOLD).vertically_centered();

        let content =
            Label::centered(reboot_msg.as_str().into(), TEXT_NORMAL).vertically_centered();

        let mut frame =
            ResultScreen::new(BLD_FG, BLD_BG, ICON_SPINNER, title, content, complete_draw);
        show(&mut frame, false);
    }

    fn screen_install_fail() {
        let title = Label::centered("Install failed".into(), TEXT_BOLD).vertically_centered();

        let content = Label::centered("Please reconnect\nthe device".into(), TEXT_NORMAL)
            .vertically_centered();

        let mut frame = ResultScreen::new(BLD_FG, BLD_BG, ICON_ALERT, title, content, true);
        show(&mut frame, false);
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
            "INSTALL FIRMWARE"
        } else if is_newvendor {
            "CHANGE FW VENDOR"
        } else if version_cmp > 0 {
            "UPDATE FIRMWARE"
        } else if version_cmp == 0 {
            "REINSTALL FW"
        } else {
            "DOWNGRADE FW"
        };

        let message =
            Label::left_aligned(version_str.as_str().into(), TEXT_NORMAL).vertically_centered();
        let fingerprint = Label::left_aligned(
            fingerprint.into(),
            TEXT_NORMAL.with_line_breaking(BreakWordsNoHyphen),
        )
        .vertically_centered();

        let alert = (!should_keep_seed).then_some(Label::left_aligned(
            "Seed will be erased!".into(),
            TEXT_NORMAL,
        ));

        let mut frame = Confirm::new(
            BLD_BG,
            title_str.into(),
            message,
            alert,
            "INSTALL".into(),
            false,
        )
        .with_info_screen("FW FINGERPRINT".into(), fingerprint);
        run(&mut frame)
    }

    fn screen_wipe_confirm() -> u32 {
        let message = Label::left_aligned("Seed and firmware will be erased!".into(), TEXT_NORMAL)
            .vertically_centered();

        let mut frame = Confirm::new(
            BLD_BG,
            "FACTORY RESET".into(),
            message,
            None,
            "RESET".into(),
            false,
        );

        run(&mut frame)
    }

    fn screen_unlock_bootloader_confirm() -> u32 {
        let message = Label::left_aligned("This action cannot be undone!".into(), TEXT_NORMAL)
            .vertically_centered();

        let mut frame = Confirm::new(
            BLD_BG,
            "UNLOCK BOOTLOADER?".into(),
            message,
            None,
            "UNLOCK".into(),
            true,
        );

        run(&mut frame)
    }

    fn screen_unlock_bootloader_success() {
        let title = Label::centered("Bootloader unlocked".into(), TEXT_BOLD).vertically_centered();

        let content = Label::centered("Please reconnect the\ndevice".into(), TEXT_NORMAL)
            .vertically_centered();

        let mut frame = ResultScreen::new(BLD_FG, BLD_BG, ICON_SPINNER, title, content, true);
        show(&mut frame, false);
    }

    fn screen_menu(firmware_present: secbool) -> u32 {
        run(&mut Menu::new(firmware_present))
    }

    fn screen_intro(bld_version: &str, vendor: &str, version: &str, fw_ok: bool) -> u32 {
        let mut title_str: BootloaderString = String::new();
        unwrap!(title_str.push_str("BOOTLOADER "));
        unwrap!(title_str.push_str(bld_version));

        let mut version_str: BootloaderString = String::new();
        unwrap!(version_str.push_str("Firmware version "));
        unwrap!(version_str.push_str(version));
        unwrap!(version_str.push_str("\nby "));
        unwrap!(version_str.push_str(vendor));

        let mut frame = Intro::new(
            title_str.as_str().into(),
            version_str.as_str().into(),
            fw_ok,
        );
        run(&mut frame)
    }

    fn screen_boot_stage_1(_fading: bool) {
        let mut frame = WelcomeScreen::new(cfg!(ui_empty_lock));
        show(&mut frame, false);
    }

    fn screen_wipe_progress(progress: u16, initialize: bool) {
        Self::screen_progress(
            "Resetting",
            "Trezor",
            progress,
            initialize,
            BLD_FG,
            BLD_BG,
            Some((ICON_SUCCESS, BLD_FG)),
        );
    }

    fn screen_install_progress(progress: u16, initialize: bool, _initial_setup: bool) {
        Self::screen_progress(
            "Installing",
            "firmware",
            progress,
            initialize,
            BLD_FG,
            BLD_BG,
            Some((ICON_SUCCESS, BLD_FG)),
        );
    }

    fn screen_connect(_initial_setup: bool) {
        let mut frame = Connect::new("Waiting for host...", fonts::FONT_NORMAL, BLD_FG, BLD_BG);
        show(&mut frame, false);
    }

    fn screen_wipe_success() {
        let title = Label::centered("Trezor Reset".into(), TEXT_BOLD).vertically_centered();

        let content = Label::centered("Please reconnect\nthe device".into(), TEXT_NORMAL)
            .vertically_centered();

        let mut frame = ResultScreen::new(BLD_FG, BLD_BG, ICON_SPINNER, title, content, true);
        show(&mut frame, false);
    }

    fn screen_wipe_fail() {
        let title = Label::centered("Reset failed".into(), TEXT_BOLD).vertically_centered();

        let content = Label::centered("Please reconnect\nthe device".into(), TEXT_NORMAL)
            .vertically_centered();

        let mut frame = ResultScreen::new(BLD_FG, BLD_BG, ICON_ALERT, title, content, true);
        show(&mut frame, false);
    }

    fn screen_boot(
        _warning: bool,
        vendor_str: Option<&str>,
        version: [u8; 4],
        vendor_img: &'static [u8],
        wait: i32,
    ) {
        display::sync();

        render_on_display(None, Some(BLD_BG), |target| {
            // Draw vendor image if it's valid and has size of 24x24
            if let Ok(toif) = Toif::new(vendor_img) {
                if (toif.width() == 24) && (toif.height() == 24) {
                    let pos = Point::new((constant::WIDTH - 22) / 2, 0);
                    shape::ToifImage::new(pos, toif)
                        .with_align(Alignment2D::TOP_CENTER)
                        .with_fg(BLD_FG)
                        .render(target);
                }
            }

            // Draw vendor string if present
            if let Some(text) = vendor_str {
                let pos = Point::new(constant::WIDTH / 2, 36);
                shape::Text::new(pos, text, fonts::FONT_NORMAL)
                    .with_align(Alignment::Center)
                    .with_fg(BLD_FG) //COLOR_BL_BG
                    .render(target);

                let pos = Point::new(constant::WIDTH / 2, 46);

                let mut version_text: BootloaderString = String::new();
                unwrap!(uwrite!(
                    version_text,
                    "{}.{}.{}",
                    version[0],
                    version[1],
                    version[2]
                ));

                shape::Text::new(pos, version_text.as_str(), fonts::FONT_NORMAL)
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

                    let pos = Point::new(constant::WIDTH / 2, HEIGHT - 5);
                    shape::Text::new(pos, text.as_str(), fonts::FONT_NORMAL)
                        .with_align(Alignment::Center)
                        .with_fg(BLD_FG)
                        .render(target);
                }
                core::cmp::Ordering::Less => {
                    let pos = Point::new(constant::WIDTH / 2, HEIGHT - 2);
                    shape::Text::new(pos, "CONTINUE", fonts::FONT_NORMAL)
                        .with_align(Alignment::Center)
                        .with_fg(BLD_FG)
                        .render(target);

                    let pos = Point::new(constant::WIDTH / 2 - 36, HEIGHT - 6);
                    shape::ToifImage::new(pos, ICON_ARM_LEFT.toif)
                        .with_align(Alignment2D::TOP_LEFT)
                        .with_fg(BLD_FG)
                        .render(target);

                    let pos = Point::new(constant::WIDTH / 2 + 25, HEIGHT - 6);
                    shape::ToifImage::new(pos, ICON_ARM_RIGHT.toif)
                        .with_align(Alignment2D::TOP_LEFT)
                        .with_fg(BLD_FG)
                        .render(target);
                }
            }
        });

        display::refresh();
    }
}
