use xbuild::{Result, build_mods};

#[path = "app_loader/build.rs"]
mod app_loader;
#[path = "backlight/build.rs"]
mod backlight;
#[path = "ble/build.rs"]
mod ble;
#[path = "button/build.rs"]
mod button;
#[path = "display/build.rs"]
mod display;
#[path = "gfx/build.rs"]
mod gfx;
#[path = "haptic/build.rs"]
mod haptic;
#[path = "nfc/build.rs"]
mod nfc;
#[path = "notify/build.rs"]
mod notify;
#[path = "nrf/build.rs"]
mod nrf;
#[path = "power_manager/build.rs"]
mod power_manager;
#[path = "rgb_led/build.rs"]
mod rgb_led;
#[path = "sbu/build.rs"]
mod sbu;
#[path = "sdcard/build.rs"]
mod sdcard;
#[path = "suspend/build.rs"]
mod suspend;
#[path = "touch/build.rs"]
mod touch;
#[path = "translations/build.rs"]
mod translations;
#[path = "tsqueue/build.rs"]
mod tsqueue;
#[path = "usb/build.rs"]
mod usb;

fn main() -> Result<()> {
    xbuild::build(|lib| {
        lib.import_lib("sec")?;

        build_mods!(
            lib,
            [
                app_loader if cfg!(feature = "app_loading"),
                backlight if cfg!(feature = "backlight"),
                ble if cfg!(feature = "ble"),
                button if cfg!(feature = "button"),
                display,
                gfx,
                haptic if cfg!(feature = "haptic"),
                notify,
                nfc if cfg!(feature = "nfc"),
                nrf if cfg!(feature = "nrf"),
                power_manager if cfg!(any(feature = "power_manager", feature = "pmic")),
                rgb_led if cfg!(feature = "rgb_led"),
                sbu if cfg!(feature = "sbu"),
                sdcard if cfg!(feature = "sd_card"),
                suspend if cfg!(feature = "suspend"),
                touch if cfg!(feature = "touch"),
                translations,
                tsqueue,
                usb if cfg!(feature = "usb"),
            ]
        );

        if cfg!(not(feature = "emulator")) && cfg!(not(feature = "kernel_mode")) {
            // Add syscall stubs when linking in in unprivileged mode
            lib.add_source("../sys/syscall/stm32/syscall_stubs.c");
        }

        Ok(())
    })
}
