use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("irq/inc");

    if cfg!(feature = "emulator") {
        // No implementation
    } else if cfg!(feature = "mcu_stm32") {
        lib.add_source("irq/stm32/irq.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
