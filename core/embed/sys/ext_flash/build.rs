use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("ext_flash/inc");
    lib.add_define("USE_EXT_FLASH", Some("1"));

    if cfg!(feature = "emulator") {
        // No hardware implementation for the emulator
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("ext_flash/stm32u5/ext_flash.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
