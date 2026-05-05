use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("pvd/inc");

    lib.add_define("USE_PVD", Some("1"));

    if cfg!(feature = "emulator") {
        lib.add_source("pvd/unix/pvd.c");
    } else if cfg!(feature = "mcu_stm32") {
        lib.add_source("pvd/stm32/pvd.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
