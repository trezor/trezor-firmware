use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("coreapp/inc");

    if cfg!(feature = "emulator") {
        lib.add_sources([
            "task/unix/coreapp.c",
        ]);
    } else if cfg!(feature = "mcu_stm32") {
        lib.add_sources([
            "task/stm32/coreapp.c",
        ]);
    } else {
        bail_unsupported!();
    }

    Ok(())
}
