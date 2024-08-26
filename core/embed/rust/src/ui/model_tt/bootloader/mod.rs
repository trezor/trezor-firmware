use heapless::String;

use crate::{
    trezorhal::secbool::secbool,
    ui::{
        component::{connect::Connect, Label},
        display::{self, Color, Font, Icon},
        geometry::{Point, Rect},
        layout::simplified::{run, show},
    },
};

use super::{
    bootloader::welcome::Welcome,
    component::{
        bl_confirm::{Confirm, ConfirmTitle},
        Button, ResultScreen, WelcomeScreen,
    },
    theme,
    theme::{
        bootloader::{
            button_bld, button_bld_menu, button_confirm, button_wipe_cancel, button_wipe_confirm,
            BLD_BG, BLD_FG, BLD_TITLE_COLOR, BLD_WIPE_COLOR, CHECK24, CHECK40, DOWNLOAD32, FIRE32,
            FIRE40, RESULT_FW_INSTALL, RESULT_INITIAL, RESULT_WIPE, TEXT_BOLD, TEXT_NORMAL,
            TEXT_WIPE_BOLD, TEXT_WIPE_NORMAL, WARNING40, WELCOME_COLOR, X24,
        },
        FG,
    },
    ModelTTFeatures,
};

use crate::ui::{ui_features::UIFeaturesBootloader, UIFeaturesCommon};

#[cfg(not(feature = "new_rendering"))]
use super::theme::BLACK;

#[cfg(feature = "new_rendering")]
use crate::ui::{
    constant,
    display::toif::Toif,
    geometry::{Alignment, Alignment2D, Offset},
    shape,
    shape::render_on_display,
};

#[cfg(feature = "new_rendering")]
use ufmt::uwrite;

#[cfg(feature = "new_rendering")]
use super::theme::bootloader::BLD_WARN_COLOR;

use intro::Intro;
use menu::Menu;

#[cfg(feature = "new_rendering")]
use super::cshape::{render_loader, LoaderRange};
#[cfg(feature = "new_rendering")]
use crate::ui::display::LOADER_MAX;

pub mod intro;
pub mod menu;
pub mod welcome;

pub type BootloaderString = String<128>;

const RECONNECT_MESSAGE: &str = "PLEASE RECONNECT\nTHE DEVICE";

const SCREEN: Rect = ModelTTFeatures::SCREEN;

impl ModelTTFeatures {
    #[cfg(not(feature = "new_rendering"))]
    fn screen_progress(
        text: &str,
        progress: u16,
        initialize: bool,
        fg_color: Color,
        bg_color: Color,
        icon: Option<(Icon, Color)>,
    ) {
        if initialize {
            Self::fadeout();
            display::rect_fill(SCREEN, bg_color);
        }

        display::text_center(
            Point::new(SCREEN.width() / 2, SCREEN.height() - 45),
            text,
            Font::NORMAL,
            fg_color,
            bg_color,
        );
        display::loader(progress, -20, fg_color, bg_color, icon);
        display::refresh();
        if initialize {
            Self::fadein();
        }
    }

    #[cfg(feature = "new_rendering")]
    fn screen_progress(
        text: &str,
        progress: u16,
        initialize: bool,
        fg_color: Color,
        bg_color: Color,
        icon: Option<(Icon, Color)>,
    ) {
        if initialize {
            Self::fadeout();
        }
        display::sync();

        render_on_display(None, Some(bg_color), |target| {
            shape::Text::new(Point::new(SCREEN.width() / 2, SCREEN.height() - 45), text)
                .with_align(Alignment::Center)
                .with_font(Font::NORMAL)
                .with_fg(fg_color)
                .render(target);

            let center = SCREEN.center() + Offset::y(-20);
            let inactive_color = bg_color.blend(fg_color, 85);
            let end = 360.0 * progress as f32 / 1000.0;

            render_loader(
                center,
                inactive_color,
                fg_color,
                bg_color,
                if progress >= LOADER_MAX {
                    LoaderRange::Full
                } else {
                    LoaderRange::FromTo(0.0, end)
                },
                target,
            );

            if let Some((icon, color)) = icon {
                shape::ToifImage::new(center, icon.toif)
                    .with_align(Alignment2D::CENTER)
                    .with_fg(color)
                    .render(target);
            }
        });

        display::refresh();
        if initialize {
            Self::fadein();
        }
    }

    fn screen_install_success_bld(msg: &str, complete_draw: bool) {
        let mut frame = ResultScreen::new(
            &RESULT_FW_INSTALL,
            Icon::new(CHECK40),
            "Firmware installed\nsuccessfully".into(),
            Label::centered(msg.into(), RESULT_FW_INSTALL.title_style()).vertically_centered(),
            complete_draw,
        );
        show(&mut frame, complete_draw);
    }

    fn screen_install_success_initial(msg: &str, complete_draw: bool) {
        let mut frame = ResultScreen::new(
            &RESULT_INITIAL,
            Icon::new(CHECK40),
            "Firmware installed\nsuccessfully".into(),
            Label::centered(msg.into(), RESULT_INITIAL.title_style()).vertically_centered(),
            complete_draw,
        );
        show(&mut frame, complete_draw);
    }
}

impl UIFeaturesBootloader for ModelTTFeatures {
    fn screen_welcome() {
        let mut frame = Welcome::new();
        show(&mut frame, true);
    }

    #[cfg(not(feature = "new_rendering"))]
    fn bld_continue_label(bg_color: Color) {
        display::text_center(
            Point::new(SCREEN.width() / 2, SCREEN.height() - 5),
            "click to continue ...",
            Font::NORMAL,
            BLD_FG,
            bg_color,
        );
    }

    fn screen_install_success(restart_seconds: u8, initial_setup: bool, complete_draw: bool) {
        let mut reboot_msg = BootloaderString::new();

        if restart_seconds >= 1 {
            unwrap!(reboot_msg.push_str("RESTARTING IN "));
            // in practice, restart_seconds is 5 or less so this is fine
            let seconds_char = b'0' + restart_seconds % 10;
            unwrap!(reboot_msg.push(seconds_char as char));
        } else {
            unwrap!(reboot_msg.push_str(RECONNECT_MESSAGE));
        }

        if initial_setup {
            Self::screen_install_success_initial(reboot_msg.as_str(), complete_draw)
        } else {
            Self::screen_install_success_bld(reboot_msg.as_str(), complete_draw)
        }
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

    fn screen_boot_stage_1(fading: bool) {
        if fading {
            Self::fadeout();
        }

        #[cfg(not(feature = "new_rendering"))]
        display::rect_fill(SCREEN, BLACK);

        let mut frame = WelcomeScreen::new(true);
        show(&mut frame, false);

        if fading {
            Self::fadein();
        } else {
            display::set_backlight(theme::backlight::get_backlight_normal());
        }
    }

    fn screen_wipe_progress(progress: u16, initialize: bool) {
        Self::screen_progress(
            "Resetting Trezor",
            progress,
            initialize,
            BLD_FG,
            BLD_WIPE_COLOR,
            Some((Icon::new(FIRE32), BLD_FG)),
        )
    }

    fn screen_install_progress(progress: u16, initialize: bool, initial_setup: bool) {
        let bg_color = if initial_setup { WELCOME_COLOR } else { BLD_BG };
        let fg_color = if initial_setup { FG } else { BLD_FG };

        Self::screen_progress(
            "Installing firmware",
            progress,
            initialize,
            fg_color,
            bg_color,
            Some((Icon::new(DOWNLOAD32), fg_color)),
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

    #[cfg(feature = "new_rendering")]
    fn screen_boot(
        warning: bool,
        vendor_str: Option<&str>,
        version: [u8; 4],
        vendor_img: &'static [u8],
        wait: i32,
    ) {
        let bg_color = if warning { BLD_WARN_COLOR } else { BLD_BG };

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
                shape::Text::new(pos, text)
                    .with_align(Alignment::Center)
                    .with_font(Font::NORMAL)
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

                shape::Text::new(pos, version_text.as_str())
                    .with_align(Alignment::Center)
                    .with_font(Font::NORMAL)
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
                    shape::Text::new(pos, text.as_str())
                        .with_align(Alignment::Center)
                        .with_font(Font::NORMAL)
                        .with_fg(BLD_FG)
                        .render(target);
                }
                core::cmp::Ordering::Less => {
                    let pos = Point::new(SCREEN.width() / 2, SCREEN.height() - 5);
                    shape::Text::new(pos, "click to continue ...")
                        .with_align(Alignment::Center)
                        .with_font(Font::NORMAL)
                        .with_fg(BLD_FG)
                        .render(target);
                }
            }
        });

        display::refresh();
    }
}
