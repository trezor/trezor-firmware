use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("i2c_bus/inc");

    if cfg!(feature = "emulator") {
        // No implementation
    } else if cfg!(feature = "mcu_stm32f4") {
        lib.add_source("i2c_bus/stm32f4/i2c_bus.c");
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("i2c_bus/stm32u5/i2c_bus.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
