use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("trustzone/inc");

    // USE_TRUSTZONE is defined in sys layer

    if cfg!(feature = "emulator") {
        lib.add_source("trustzone/unix/tz_init.c");
    } else if cfg!(feature = "mcu_stm32") {
        lib.add_source("trustzone/stm32u5/tz_init.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
