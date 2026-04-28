use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("sbu/inc");

    lib.add_define("USE_SBU", Some("1"));

    if cfg!(feature = "emulator") {
        lib.add_source("sbu/unix/sbu.c");
    } else if cfg!(feature = "mcu_stm32") {
        lib.add_source("sbu/stm32/sbu.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
