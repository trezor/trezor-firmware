use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("dbg/inc");

    lib.add_define("USE_DBG_CONSOLE", Some("1"));

    lib.add_sources(["dbg/dbg_console.c", "dbg/syslog.c"]);

    if cfg!(feature = "emulator") {
        lib.add_source("dbg/unix/dbg_console_backend.c");
    } else if cfg!(feature = "mcu_stm32") {
        lib.add_source("dbg/stm32/dbg_console_backend.c");

        if cfg!(feature = "block_on_vcp") {
            lib.add_define("BLOCK_ON_VCP", None);
        }

        if cfg!(feature = "system_view") {
            def_system_view(lib);
        }
    } else {
        bail_unsupported!();
    }

    Ok(())
}

fn def_system_view(lib: &mut CLibrary) {
    lib.add_define("USE_SYSTEM_VIEW", Some("1"));

    lib.add_includes(["dbg/stm32/systemview/config", "dbg/stm32/systemview/segger"]);

    lib.add_sources_from_folder(
        "dbg/stm32/systemview",
        [
            "config/SEGGER_SYSVIEW_Config_NoOS.c",
            "segger/SEGGER_SYSVIEW.c",
            "segger/SEGGER_RTT.c",
            "segger/SEGGER_RTT_ASM_ARMv7M.S",
        ],
    );
}
