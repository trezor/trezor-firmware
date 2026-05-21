use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("hw_revision/inc");

    lib.add_define("USE_HW_REVISION", Some("1"));

    if cfg!(feature = "emulator") {
        lib.add_source("hw_revision/unix/hw_revision.c");
    } else if cfg!(feature = "mcu_stm32") {
        lib.add_source("hw_revision/stm32/hw_revision.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
