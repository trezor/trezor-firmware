use xbuild::Result;

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

#[path = "haptic/build.rs"]
mod haptic;

#[path = "gfx/build.rs"]
mod gfx;

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

#[path = "translations/build.rs"]
mod translations;

#[path = "tsqueue/build.rs"]
mod tsqueue;

#[path = "touch/build.rs"]
mod touch;

#[path = "usb/build.rs"]
mod usb;

fn main() -> Result<()> {
    xbuild::build(|lib| {
        lib.import_lib("sec")?;

        if cfg!(feature = "app_loading") {
            app_loader::def_module(lib)?;
        }

        if cfg!(feature = "backlight") {
            backlight::def_module(lib)?;
        }

        if cfg!(feature = "ble") {
            ble::def_module(lib)?;
        }

        if cfg!(feature = "button") {
            button::def_module(lib)?;
        }

        display::def_module(lib)?;

        gfx::def_module(lib)?;

        if cfg!(feature = "haptic") {
            haptic::def_module(lib)?;
        }

        notify::def_module(lib)?;

        if cfg!(feature = "nrf") {
            nrf::def_module(lib)?;
        }

        //TODO: consider splitting pmic/power_manager into separate modules
        if cfg!(feature = "power_manager") || cfg!(feature = "pmic") {
            power_manager::def_module(lib)?;
        }

        if cfg!(feature = "rgb_led") {
            rgb_led::def_module(lib)?;
        }

        if cfg!(feature = "sbu") {
            sbu::def_module(lib)?;
        }

        if cfg!(feature = "sd_card") {
            sdcard::def_module(lib)?;
        }

        if cfg!(feature = "suspend") {
            suspend::def_module(lib)?;
        }

        translations::def_module(lib)?;

        tsqueue::def_module(lib)?;

        if cfg!(feature = "touch") {
            touch::def_module(lib)?;
        }

        if cfg!(feature = "usb") {
            usb::def_module(lib)?;
        }

        if cfg!(not(feature = "emulator")) && cfg!(not(feature = "kernel_mode")) {
            // Add syscall stubs when linking in in unprivileged mode
            lib.add_source("../sys/syscall/stm32/syscall_stubs.c");
        }

        Ok(())
    })
}
