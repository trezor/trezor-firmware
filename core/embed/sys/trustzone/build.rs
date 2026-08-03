use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("trustzone/inc");

    lib.add_define("USE_TRUSTZONE", Some("1"));

    if cfg!(feature = "emulator") {
        // No implementation
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("trustzone/stm32u5/trustzone.c");
    } else if cfg!(feature = "mcu_stm32h5") {
        lib.add_source("trustzone/stm32h5/trustzone.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
