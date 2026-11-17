use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("monoctr/inc");

    if cfg!(feature = "emulator") {
        lib.add_source("monoctr/unix/monoctr.c");
    } else if cfg!(feature = "mcu_stm32u5") || cfg!(feature = "mcu_stm32h5") {
        // The monotonic counters live in the secret flash area and are accessed
        // only through the secret_/flash_area abstractions, so this
        // implementation is MCU-agnostic and shared by all M33 secret-based
        // targets (STM32U5, STM32H5).
        lib.add_source("monoctr/stm32u5/monoctr.c");
    } else if cfg!(feature = "mcu_stm32f4") {
        lib.add_source("monoctr/stm32f4/monoctr.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
