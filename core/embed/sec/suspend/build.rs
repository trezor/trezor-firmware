use xbuild::{CLibrary, Result, bail_unsupported};

// Define sec/suspend module
pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("suspend/inc");

    lib.add_define("USE_SUSPEND", Some("1"));

    if cfg!(feature = "emulator") {
        // No implementation
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("suspend/stm32u5/suspend_io.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
