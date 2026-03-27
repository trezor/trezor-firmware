use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("backlight/inc");

    lib.add_define("USE_BACKLIGHT", Some("1"));

    if cfg!(feature = "emulator") {
        // No implementation
    } else if cfg!(feature = "backlight_tps61043") {
        if cfg!(feature = "mcu_stm32") {
            lib.add_source("backlight/stm32/tps61043.c");
        } else {
            bail_unsupported!();
        }
    } else if cfg!(feature = "backlight_tps61062") {
        if cfg!(feature = "mcu_stm32u5") {
            lib.add_source("backlight/stm32u5/tps61062.c");
        } else {
            bail_unsupported!();
        }
    } else {
        bail_unsupported!();
    }

    Ok(())
}
