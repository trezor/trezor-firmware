use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    if cfg!(feature = "emulator") {
        // No implementation
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_include("hash_processor/inc");
        lib.add_define("USE_HASH_PROCESSOR", Some("1"));
        lib.add_source("hash_processor/stm32u5/hash_processor.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
