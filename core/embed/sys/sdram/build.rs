use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("sdram/inc");

    lib.add_define("USE_SDRAM", Some("1"));

    if cfg!(feature = "emulator") {
        // No implementation
    } else if cfg!(feature = "sdram_stm32f429i_disc1") {
        lib.add_source("sdram/stm32f429i-disc1/sdram_bsp.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
