use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("sdcard/inc");

    lib.add_define("USE_SD_CARD", Some("1"));

    if cfg!(feature = "emulator") {
        lib.add_source("sdcard/unix/sdcard.c");
    } else if cfg!(feature = "mcu_stm32f4") {
        lib.add_source("sdcard/stm32f4/sdcard.c");
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("sdcard/stm32u5/sdcard.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
