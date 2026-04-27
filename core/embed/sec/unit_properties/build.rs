use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("unit_properties/inc");

    if cfg!(feature = "emulator") {
        lib.add_source("unit_properties/unix/unit_properties.c");
    } else if cfg!(feature = "mcu_stm32") {
        lib.add_source("unit_properties/stm32/unit_properties.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
