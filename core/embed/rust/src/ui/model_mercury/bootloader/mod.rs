use heapless::String;

use crate::{
    trezorhal::secbool::secbool,
    ui::{
        component::{connect::Connect, Label},
        display::{self, Color, Font, Icon},
        geometry::{Offset, Point, Rect},
        layout::simplified::{run, show},
    },
};

use super::{
    bootloader::welcome::Welcome,
    component::{
        bl_confirm::{Confirm, ConfirmTitle},
        Button, ResultScreen, WelcomeScreen,
    },
    theme::{
        bootloader::{
            button_bld, button_bld_menu, button_confirm, button_wipe_cancel, button_wipe_confirm,
            BLD_BG, BLD_FG, BLD_TITLE_COLOR, BLD_WIPE_COLOR, CHECK24, CHECK40, DOWNLOAD24, FIRE32,
            FIRE40, RESULT_FW_INSTALL, RESULT_WIPE, TEXT_BOLD, TEXT_NORMAL, TEXT_WIPE_BOLD,
            TEXT_WIPE_NORMAL, WARNING40, WELCOME_COLOR, X24,
        },
        BACKLIGHT_NORMAL, BLACK, GREEN_LIGHT, GREY, WHITE,
    },
    ModelMercuryFeatures,
};

use crate::ui::{ui_features::UIFeaturesBootloader, UIFeaturesCommon};
use intro::Intro;
use menu::Menu;

pub mod intro;
pub mod menu;
pub mod welcome;

pub type BootloaderString = String<128>;

const RECONNECT_MESSAGE: &str = "PLEASE RECONNECT\nTHE DEVICE";

const SCREEN: Rect = ModelMercuryFeatures::SCREEN;
const PROGRESS_TEXT_ORIGIN: Point = Point::new(2, 28);

impl ModelMercuryFeatures {
    fn screen_progress(
        text: &str,
        progress: u16,
        initialize: bool,
        fg_color: Color,
        bg_color: Color,
        icon: Option<(Icon, Color)>,
        center_text: Option<&str>,
    ) {
        let loader_offset: i16 = 19;
        let center_text_offset: i16 = 10;

        if initialize {
            Self::fadeout();
            display::rect_fill(SCREEN, bg_color);
        }

        display::text_left(PROGRESS_TEXT_ORIGIN, text, Font::NORMAL, BLD_FG, bg_color);
        display::loader(progress, 19, fg_color, bg_color, icon);
        if let Some(center_text) = center_text {
            display::text_center(
                SCREEN.center() + Offset::y(loader_offset + center_text_offset),
                center_text,
                Font::NORMAL,
                GREY,
                bg_color,
            );
        }
        display::refresh();
        if initialize {
            Self::fadein();
        }
    }
}

impl UIFeaturesBootloader for ModelMercuryFeatures {
    fn screen_welcome() {
        let mut frame = Welcome::new();
        show(&mut frame, true);
    }

    fn bld_continue_label(bg_color: Color) {
        display::text_center(
            Point::new(SCREEN.width() / 2, SCREEN.height() - 5),
            "click to continue ...",
            Font::NORMAL,
            WHITE,
            bg_color,
        );
    }

    fn screen_install_success(restart_seconds: u8, initial_setup: bool, complete_draw: bool) {
        let mut reboot_msg = BootloaderString::new();

        let bg_color = if initial_setup { WELCOME_COLOR } else { BLD_BG };
        let fg_color = if initial_setup { GREEN_LIGHT } else { BLD_FG };

        if restart_seconds >= 1 {
            // in practice, restart_seconds is 5 or less so this is fine
            let seconds_char = b'0' + restart_seconds % 10;
            unwrap!(reboot_msg.push(seconds_char as char));
            let progress = (5 - (restart_seconds as u16)).clamp(0, 5) * 200;

            Self::screen_progress(
                "Restarting device",
                progress,
                complete_draw,
                fg_color,
                bg_color,
                None,
                Some(reboot_msg.as_str()),
            );
        } else {
            Self::screen_progress(
                "Firmware installed",
                1000,
                complete_draw,
                fg_color,
                bg_color,
                Some((Icon::new(CHECK24), BLD_FG)),
                None,
            );
        }

        display::refresh();
    }

    fn screen_install_fail() {
        let mut frame = ResultScreen::new(
            &RESULT_FW_INSTALL,
            Icon::new(WARNING40),
            "Firmware installation was not successful".into(),
            Label::centered(RECONNECT_MESSAGE.into(), RESULT_FW_INSTALL.title_style())
                .vertically_centered(),
            true,
        );
        show(&mut frame, true);
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
            "CHANGE FW\nVENDOR"
        } else if version_cmp > 0 {
            "UPDATE FIRMWARE"
        } else if version_cmp == 0 {
            "REINSTALL FW"
        } else {
            "DOWNGRADE FW"
        };
        let title = Label::left_aligned(title_str.into(), TEXT_BOLD).vertically_centered();
        let msg = Label::left_aligned(version_str.as_str().into(), TEXT_NORMAL);
        let alert = (!should_keep_seed).then_some(Label::left_aligned(
            "SEED WILL BE ERASED!".into(),
            TEXT_BOLD,
        ));

        let (left, right) = if should_keep_seed {
            let l = Button::with_text("CANCEL".into()).styled(button_bld());
            let r = Button::with_text("INSTALL".into()).styled(button_confirm());
            (l, r)
        } else {
            let l = Button::with_icon(Icon::new(X24)).styled(button_bld());
            let r = Button::with_icon(Icon::new(CHECK24)).styled(button_confirm());
            (l, r)
        };

        let mut frame = Confirm::new(BLD_BG, left, right, ConfirmTitle::Text(title), msg)
            .with_info(
                "FW FINGERPRINT".into(),
                fingerprint.into(),
                button_bld_menu(),
            );

        if let Some(alert) = alert {
            frame = frame.with_alert(alert);
        }

        run(&mut frame)
    }

    fn screen_wipe_confirm() -> u32 {
        let icon = Icon::new(FIRE40);

        let msg = Label::centered(
            "Are you sure you want to factory reset the device?".into(),
            TEXT_WIPE_NORMAL,
        );
        let alert = Label::centered("SEED AND FIRMWARE\nWILL BE ERASED!".into(), TEXT_WIPE_BOLD);

        let right = Button::with_text("RESET".into()).styled(button_wipe_confirm());
        let left = Button::with_text("CANCEL".into()).styled(button_wipe_cancel());

        let mut frame = Confirm::new(BLD_WIPE_COLOR, left, right, ConfirmTitle::Icon(icon), msg)
            .with_alert(alert);

        run(&mut frame)
    }

    fn screen_unlock_bootloader_confirm() -> u32 {
        unimplemented!();
    }

    fn screen_unlock_bootloader_success() {
        unimplemented!();
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

    fn screen_boot_empty(fading: bool) {
        if fading {
            Self::fadeout();
        }

        display::rect_fill(SCREEN, BLACK);

        let mut frame = WelcomeScreen::new();
        show(&mut frame, false);

        if fading {
            Self::fadein();
        } else {
            display::set_backlight(BACKLIGHT_NORMAL);
        }
        display::refresh();
    }

    fn screen_wipe_progress(progress: u16, initialize: bool) {
        Self::screen_progress(
            "Resetting Trezor",
            progress,
            initialize,
            BLD_FG,
            BLD_WIPE_COLOR,
            Some((Icon::new(FIRE32), BLD_FG)),
            None,
        )
    }

    fn screen_install_progress(progress: u16, initialize: bool, initial_setup: bool) {
        let bg_color = if initial_setup { WELCOME_COLOR } else { BLD_BG };
        let fg_color = if initial_setup { GREEN_LIGHT } else { BLD_FG };
        let icon_color = BLD_FG;

        Self::screen_progress(
            "Installing firmware",
            progress,
            initialize,
            fg_color,
            bg_color,
            Some((Icon::new(DOWNLOAD24), icon_color)),
            None,
        )
    }

    fn screen_connect(initial_setup: bool) {
        let bg = if initial_setup { WELCOME_COLOR } else { BLD_BG };
        let mut frame = Connect::new("Waiting for host...", BLD_TITLE_COLOR, bg);
        show(&mut frame, true);
    }

    fn screen_wipe_success() {
        let mut frame = ResultScreen::new(
            &RESULT_WIPE,
            Icon::new(CHECK40),
            "Trezor reset\nsuccessfully".into(),
            Label::centered(RECONNECT_MESSAGE.into(), RESULT_WIPE.title_style())
                .vertically_centered(),
            true,
        );
        show(&mut frame, true);
    }

    fn screen_wipe_fail() {
        let mut frame = ResultScreen::new(
            &RESULT_WIPE,
            Icon::new(WARNING40),
            "Trezor reset was\nnot successful".into(),
            Label::centered(RECONNECT_MESSAGE.into(), RESULT_WIPE.title_style())
                .vertically_centered(),
            true,
        );
        show(&mut frame, true);
    }
}
