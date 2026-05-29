use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("rng/inc");

    if cfg!(feature = "emulator") {
        lib.add_source("rng/unix/rng.c");
    } else if cfg!(feature = "mcu_stm32") {
        lib.add_source("rng/stm32/rng.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
