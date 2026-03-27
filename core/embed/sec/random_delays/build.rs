use xbuild::{CLibrary, Result, bail_unsupported};

// Define sec/random_delays module
pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("random_delays/inc");

    if cfg!(feature = "random_delays") {
        lib.add_define("RDI", Some("1"));
    }

    if cfg!(feature = "emulator") {
        lib.add_source("random_delays/unix/random_delays.c");
    } else if cfg!(feature = "mcu_stm32") {
        lib.add_source("random_delays/stm32/random_delays.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
