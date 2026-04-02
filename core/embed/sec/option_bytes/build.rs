use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("option_bytes/inc");

    if cfg!(feature = "emulator") {
        // No implementation
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("option_bytes/stm32u5/option_bytes.c");
    } else if cfg!(feature = "mcu_stm32f4") {
        lib.add_source("option_bytes/stm32f4/option_bytes.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
