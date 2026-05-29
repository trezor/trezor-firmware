use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("suspend/inc");

    // `USE_SUSPEND` is defined in sec layer

    if cfg!(feature = "emulator") {
        // No implementation
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_sources(["suspend/stm32u5/suspend_io.c", "suspend/stm32u5/suspend.c"]);
    } else {
        bail_unsupported!();
    }

    Ok(())
}
