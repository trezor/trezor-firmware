use heapless::String;

use crate::{
    trezorhal::secbool::secbool,
    ui::{
        component::{connect::Connect, Label, LineBreaking::BreakWordsNoHyphen},
        constant,
        constant::{HEIGHT, SCREEN},
        display::{self, Color, Font, Icon},
        geometry::{Alignment2D, Offset, Point, Rect},
        layout::simplified::{run, show, ReturnToC},
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
    ModelTRFeatures,
};

mod intro;
mod menu;
mod welcome;

use crate::ui::ui_features::UIFeaturesBootloader;
use intro::Intro;
use menu::Menu;
use welcome::Welcome;

pub type BootloaderString = String<128>;

impl ReturnToC for ConfirmMsg {
    fn return_to_c(self) -> u32 {
        self as u32
    }
}

impl ModelTRFeatures {
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
}

impl UIFeaturesBootloader for ModelTRFeatures {
    fn screen_welcome() {
        let mut frame = Welcome::new();
        show(&mut frame, true);
    }

    fn bld_continue_label(bg_color: Color) {
        display::text_center(
            Point::new(constant::WIDTH / 2, HEIGHT - 2),
            "CONTINUE",
            Font::NORMAL,
            WHITE,
            bg_color,
        );
        ICON_ARM_LEFT.draw(
            Point::new(constant::WIDTH / 2 - 36, HEIGHT - 6),
            Alignment2D::TOP_LEFT,
            WHITE,
            bg_color,
        );
        ICON_ARM_RIGHT.draw(
            Point::new(constant::WIDTH / 2 + 25, HEIGHT - 6),
            Alignment2D::TOP_LEFT,
            WHITE,
            bg_color,
        );
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
        version_cmp: i32,
    ) -> u32 {
        let mut version_str: BootloaderString = String::new();
        unwrap!(version_str.push_str("Firmware version "));
        unwrap!(version_str.push_str(version));
        unwrap!(version_str.push_str("\nby "));
        unwrap!(version_str.push_str(vendor));

        let title_str = if is_newvendor {
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
        display::rect_fill(SCREEN, BLD_BG);

        let mut frame = WelcomeScreen::new(true);
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
        let mut frame = Connect::new("Waiting for host...", BLD_FG, BLD_BG);
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
}
