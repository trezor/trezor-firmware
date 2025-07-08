use crate::{
    strutil::TString,
    ui::{
        component::{Event, Label},
        display::{self, toif::Toif, Color},
        geometry::{Alignment, Alignment2D, Offset, Point, Rect},
        layout::simplified::{process_frame_event, run, show},
        shape::{self, render_on_display},
        ui_bootloader::{BootloaderLayoutType, BootloaderUI},
        CommonUI,
    },
};

use heapless::String;
use ufmt::uwrite;

use super::{
    bootloader::{
        BldActionBar, BldHeader, BldHeaderMsg, BldMenuScreen, BldTextScreen, BldWelcomeScreen,
        ConnectScreen,
    },
    component::Button,
    cshape::{render_loader, ScreenBorder},
    fonts,
    theme::{
        self,
        bootloader::{
            button_cancel, button_confirm, button_wipe_confirm, BLD_BG, BLD_FG,
            TEXT_FW_FINGERPRINT, TEXT_WARNING, WELCOME_COLOR,
        },
        button_default, BLUE, GREY, ICON_CHECKMARK, ICON_CLOSE, ICON_CROSS, RED, TEXT_NORMAL,
        TEXT_SMALL_GREY,
    },
    UIEckhart, WAIT_FOR_RESTART_MESSAGE,
};

#[cfg(feature = "ble")]
use super::bootloader::{ConfirmPairingScreen, PairingFinalizationScreen, PairingModeScreen};

pub type BootloaderString = String<128>;

const SCREEN: Rect = UIEckhart::SCREEN;
const PROGRESS_TEXT_ORIGIN: Point = SCREEN
    .top_left()
    .ofs(Offset::new(theme::PADDING, theme::HEADER_HEIGHT));
const SCREEN_BORDER_BLUE: ScreenBorder = ScreenBorder::new(BLUE);
const SCREEN_BORDER_RED: ScreenBorder = ScreenBorder::new(RED);

impl UIEckhart {
    fn screen_progress(
        text: &str,
        progress: u16,
        initialize: bool,
        loader_color: Color,
        center_text: Option<&str>,
    ) {
        if initialize {
            Self::fadeout();
        }
        display::sync();

        render_on_display(None, Some(BLD_BG), |target| {
            let border: &ScreenBorder = match loader_color {
                RED => &SCREEN_BORDER_RED,
                _ => &SCREEN_BORDER_BLUE,
            };
            render_loader(progress, border, target);

            shape::Text::new(PROGRESS_TEXT_ORIGIN, text, fonts::FONT_SATOSHI_REGULAR_38)
                .with_align(Alignment::Start)
                .with_fg(BLD_FG)
                .render(target);

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

#[allow(clippy::large_enum_variant)]
pub enum BootloaderLayout {
    Welcome(BldWelcomeScreen),
    Menu(BldMenuScreen),
    Connect(ConnectScreen),
    #[cfg(feature = "ble")]
    PairingMode(PairingModeScreen),
    #[cfg(feature = "ble")]
    WirelessSetup(PairingModeScreen),
    #[cfg(feature = "ble")]
    WirelessSetupFinal(ConnectScreen),
}

impl BootloaderLayoutType for BootloaderLayout {
    fn event(&mut self, event: Option<Event>) -> u32 {
        match self {
            BootloaderLayout::Welcome(f) => process_frame_event::<BldWelcomeScreen>(f, event),
            BootloaderLayout::Menu(f) => process_frame_event::<BldMenuScreen>(f, event),
            BootloaderLayout::Connect(f) => process_frame_event::<ConnectScreen>(f, event),
            #[cfg(feature = "ble")]
            BootloaderLayout::PairingMode(f) => process_frame_event::<PairingModeScreen>(f, event),
            #[cfg(feature = "ble")]
            BootloaderLayout::WirelessSetup(f) => {
                process_frame_event::<PairingModeScreen>(f, event)
            }
            #[cfg(feature = "ble")]
            BootloaderLayout::WirelessSetupFinal(f) => {
                process_frame_event::<ConnectScreen>(f, event)
            }
        }
    }

    fn show(&mut self) {
        match self {
            BootloaderLayout::Welcome(f) => show(f, true),
            BootloaderLayout::Menu(f) => show(f, true),
            BootloaderLayout::Connect(f) => show(f, true),
            #[cfg(feature = "ble")]
            BootloaderLayout::PairingMode(f) => show(f, true),
            #[cfg(feature = "ble")]
            BootloaderLayout::WirelessSetup(f) => show(f, true),
            #[cfg(feature = "ble")]
            BootloaderLayout::WirelessSetupFinal(f) => show(f, true),
        }
    }

    fn init_welcome() -> Self {
        // TODO: different UI. needs to decide based on some host already paired:
        // peer_count() > 0
        let screen = BldWelcomeScreen::new();
        Self::Welcome(screen)
    }

    fn init_menu(_initial_setup: bool) -> Self {
        Self::Menu(BldMenuScreen::new())
    }

    fn init_connect(_initial_setup: bool, auto_update: bool) -> Self {
        // TODO: different style for initial setup
        let btn = Button::with_text("Cancel".into()).styled(button_default());
        let mut screen = ConnectScreen::new("Waiting for host...".into())
            .with_action_bar(BldActionBar::new_single(btn));
        if auto_update {
            screen = screen.with_header(BldHeader::new(TString::empty()).with_menu_button());
        }

        Self::Connect(screen)
    }

    #[cfg(feature = "ble")]
    fn init_pairing_mode(_initial_setup: bool, name: &'static str) -> Self {
        // TODO: different style for initial setup
        let btn = Button::with_text("Cancel".into()).styled(button_default());
        let screen = PairingModeScreen::new("Waiting for pairing...".into(), name.into())
            .with_action_bar(BldActionBar::new_single(btn));
        Self::PairingMode(screen)
    }

    #[cfg(feature = "ble")]
    fn init_wireless_setup(name: &'static str) -> Self {
        // todo implement correct UI
        let btn = Button::with_text("Cancel".into()).styled(button_default());

        let screen = PairingModeScreen::new("QR_CODE".into(), name.into())
            .with_action_bar(BldActionBar::new_single(btn));
        Self::WirelessSetup(screen)
    }
}

impl BootloaderUI for UIEckhart {
    type CLayoutType = BootloaderLayout;

    fn screen_install_success(restart_seconds: u8, _initial_setup: bool, complete_draw: bool) {
        let mut reboot_msg = BootloaderString::new();

        let loader_color = theme::BLUE;
        if restart_seconds >= 1 {
            // in practice, restart_seconds is 5 or less so this is fine
            let seconds_char = b'0' + restart_seconds % 10;
            unwrap!(reboot_msg.push(seconds_char as char));
            let progress = (5 - (restart_seconds as u16)).clamp(0, 5) * 200;

            Self::screen_progress(
                "Restarting device",
                progress,
                complete_draw,
                loader_color,
                Some(reboot_msg.as_str()),
            );
        } else {
            Self::screen_progress(
                "Firmware installed",
                1000,
                complete_draw,
                loader_color,
                None,
            );
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
            screen = screen.with_secondary_text(alert);
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
            .with_secondary_text(alert)
            .with_header(BldHeader::new_pay_attention())
            .with_action_bar(BldActionBar::new_double(left, right))
            .with_screen_border(SCREEN_BORDER_RED);

        run(&mut screen)
    }

    fn screen_unlock_bootloader_confirm() -> u32 {
        let msg1 =
            Label::left_aligned("Unlock bootloader".into(), TEXT_NORMAL).vertically_centered();
        let msg2 = Label::left_aligned("This action cannot be undone!".into(), TEXT_NORMAL);

        let right = Button::with_text("Unlock".into()).styled(button_wipe_confirm());
        let left = Button::with_icon(theme::ICON_CHEVRON_LEFT).styled(button_cancel());

        let mut screen = BldTextScreen::new(msg1)
            .with_secondary_text(msg2)
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
        .with_header(BldHeader::new_done())
        .with_action_bar(BldActionBar::new_single(
            Button::with_text("Restart".into()).styled(button_cancel()),
        ))
        .with_screen_border(SCREEN_BORDER_RED);

        run(&mut screen);
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
            screen = screen.with_secondary_text(
                Label::new("FIRMWARE CORRUPTED".into(), Alignment::Start, TEXT_WARNING)
                    .vertically_centered(),
            );
        }

        run(&mut screen)
    }

    fn screen_boot_stage_1(_fading: bool) {}

    fn screen_wipe_progress(progress: u16, initialize: bool) {
        Self::screen_progress("Resetting Trezor", progress, initialize, theme::RED, None)
    }

    fn screen_install_progress(progress: u16, initialize: bool, _initial_setup: bool) {
        Self::screen_progress(
            "Installing firmware",
            progress,
            initialize,
            theme::BLUE,
            None,
        )
    }

    fn screen_wipe_success() {
        let mut screen = BldTextScreen::new(Label::new(
            "Trezor reset successfully".into(),
            Alignment::Start,
            TEXT_NORMAL,
        ))
        .with_header(BldHeader::new_done())
        .with_action_bar(BldActionBar::new_single(
            Button::with_text("Restart".into()).styled(button_default()),
        ))
        .with_screen_border(SCREEN_BORDER_RED);

        run(&mut screen);
    }

    fn screen_wipe_fail() {
        let mut screen = BldTextScreen::new(Label::new(
            "Trezor reset was\nnot successful".into(),
            Alignment::Start,
            TEXT_NORMAL,
        ))
        .with_header(BldHeader::new_pay_attention())
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

    #[cfg(feature = "ble")]
    fn screen_confirm_pairing(code: u32, _initial_setup: bool) -> u32 {
        let (right, left) = (
            // TODO: different style for initial setup
            Button::with_text("Confirm".into())
                .styled(button_confirm())
                .with_text_align(Alignment::Center),
            Button::with_text("Reject".into())
                .styled(button_cancel())
                .with_text_align(Alignment::Center),
        );

        let mut screen = ConfirmPairingScreen::new(code)
            .with_header(BldHeader::new("Pair device".into()))
            .with_action_bar(BldActionBar::new_double(left, right));

        run(&mut screen)
    }

    #[cfg(feature = "ble")]
    fn screen_pairing_mode_finalizing(_initial_setup: bool) -> u32 {
        // TODO: different style for initial setup
        let btn = Button::with_text("Cancel".into()).styled(button_default());

        let mut screen = PairingFinalizationScreen::new("Waiting for host confirmation...".into())
            .with_action_bar(BldActionBar::new_single(btn));

        run(&mut screen)
    }
}
