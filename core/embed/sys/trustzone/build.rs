use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("trustzone/inc");

    lib.add_define("USE_TRUSTZONE", Some("1"));

    if cfg!(feature = "emulator") {
        // No implementation
    } else if cfg!(feature = "mcu_stm32u5") || cfg!(feature = "mcu_stm32h5") {
        // Shared M33 GTZC/TrustZone driver for STM32U5 and STM32H5. The SRAM
        // bank layout and flash bank size differ and are #if-guarded inside.
        lib.add_source("trustzone/stm32u5/trustzone.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
