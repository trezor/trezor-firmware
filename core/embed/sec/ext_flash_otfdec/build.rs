use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("ext_flash_otfdec/inc");
    lib.add_define("USE_EXT_FLASH_OTFDEC", Some("1"));

    if cfg!(feature = "emulator") {
        // No hardware OTFDEC on the emulator; the module compiles to nothing.
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("ext_flash_otfdec/stm32u5/ext_flash_otfdec.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
