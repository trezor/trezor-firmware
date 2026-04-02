use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("consumption_mask/inc");

    lib.add_define("USE_CONSUMPTION_MASK", Some("1"));

    if cfg!(feature = "emulator") {
        lib.add_source("consumption_mask/unix/consumption_mask.c");
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("consumption_mask/stm32u5/consumption_mask.c");
    } else if cfg!(feature = "mcu_stm32f4") {
        lib.add_source("consumption_mask/stm32f4/consumption_mask.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
