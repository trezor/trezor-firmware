use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("task/inc");

    lib.add_sources(["task/applet.c", "task/system.c", "task/sysevent.c"]);

    if cfg!(feature = "app_loading") {
        lib.add_define("USE_APP_LOADING", Some("1"));
    }

    if cfg!(feature = "emulator") {
        lib.add_sources([
            "task/unix/coreapp.c",
            "task/unix/sdl_event.c",
            "task/unix/systask.c",
            "task/unix/system.c",
        ]);
    } else if cfg!(feature = "mcu_stm32") {
        lib.add_sources([
            "task/stm32/coreapp.c",
            "task/stm32/systask.c",
            "task/stm32/system.c",
        ]);
    } else {
        bail_unsupported!();
    }

    Ok(())
}
