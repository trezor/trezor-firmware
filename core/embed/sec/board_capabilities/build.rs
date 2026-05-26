use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("board_capabilities/inc");

    if cfg!(feature = "emulator") {
        lib.add_source("board_capabilities/unix/board_capabilities.c");
    } else if cfg!(feature = "mcu_stm32") {
        lib.add_source("board_capabilities/stm32/board_capabilities.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
