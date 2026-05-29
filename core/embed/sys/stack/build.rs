use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("stack/inc");

    if cfg!(feature = "emulator") {
        // No implementation
    } else if cfg!(feature = "mcu_stm32") {
        lib.add_source("stack/stm32/stack_utils.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
