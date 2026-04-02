use xbuild::{Result, build_mods};

fn main() -> Result<()> {
    xbuild::build(|lib| {
        lib.import_lib("sec")?;

        build_mods!(lib;
            app_loader if cfg!(feature = "app_loading"),
            backlight if cfg!(feature = "backlight"),
            ble if cfg!(feature = "ble"),
            button if cfg!(feature = "button"),
            display,
            gfx,
            haptic if cfg!(feature = "haptic"),
            notify,
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
        );

        if cfg!(not(feature = "emulator")) && cfg!(not(feature = "kernel_mode")) {
            // Add syscall stubs when linking in in unprivileged mode
            lib.add_source("../sys/syscall/stm32/syscall_stubs.c");
        }

        Ok(())
    })
}
