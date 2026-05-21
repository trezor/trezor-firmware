use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("app_loader/inc");

    // USE_APP_LOADING is defined in sys layer

    lib.add_sources([
        "app_loader/app_arena.c",
        "app_loader/app_task.c",
        "app_loader/app_cache.c",
    ]);

    if cfg!(feature = "emulator") {
        lib.add_source("app_loader/unix/elf_loader.c");
    } else if cfg!(feature = "mcu_stm32") {
        lib.add_source("app_loader/stm32/app_loader.c");
    } else {
        bail_unsupported!();
    }

    // TODO! @# define THREAD_LOCAL

    Ok(())
}
