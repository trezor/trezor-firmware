use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("app_arena/inc");

    // USE_APP_LOADING is defined in sys layer
    lib.add_source("app_arena/app_arena.c");

    if cfg!(feature = "emulator") {
        lib.add_source("app_arena/unix/xbin_loader.c");
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_sources(["app_arena/stm32u5/xbin_loader.c"]);
    } else {
        bail_unsupported!();
    }

    Ok(())
}
