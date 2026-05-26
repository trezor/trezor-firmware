use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("haptic/inc");

    lib.add_define("USE_HAPTIC", Some("1"));

    if cfg!(feature = "emulator") {
        lib.add_source("haptic/unix/haptic.c");
    } else if cfg!(feature = "mcu_stm32") {
        lib.add_source("haptic/drv262x/drv262x.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
