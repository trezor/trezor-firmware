use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("iwdg/inc");

    lib.add_define("USE_IWDG", Some("1"));

    if cfg!(feature = "emulator") {
        lib.add_source("iwdg/unix/iwdg.c");
    } else if cfg!(feature = "mcu_stm32") {
        lib.add_source("iwdg/stm32/iwdg.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
