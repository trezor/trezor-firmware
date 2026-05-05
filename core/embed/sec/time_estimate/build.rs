use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("time_estimate/inc");

    if cfg!(feature = "emulator") {
        lib.add_source("time_estimate/unix/time_estimate.c");
    } else if cfg!(feature = "mcu_stm32") {
        lib.add_source("time_estimate/stm32/time_estimate.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
