use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("ipc/inc");

    lib.add_define("USE_IPC", Some("1"));

    lib.add_source("ipc/ipc.c");

    if cfg!(feature = "emulator") {
        lib.add_source("ipc/unix/ipc_memcpy.c");
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("ipc/stm32u5/ipc_memcpy.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
