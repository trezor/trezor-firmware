use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("cpuid/inc");

    if cfg!(feature = "emulator") {
        lib.add_source("cpuid/unix/cpuid.c");
    } else if cfg!(feature = "mcu_stm32") {
        lib.add_source("cpuid/stm32/cpuid.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
