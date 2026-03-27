use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("app_loader/inc");

    lib.add_define("USE_APP_LOADING", Some("1"));

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

    Ok(())
}
