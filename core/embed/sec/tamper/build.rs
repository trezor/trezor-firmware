use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("tamper/inc");

    lib.add_define("USE_TAMPER", Some("1"));

    if cfg!(feature = "emulator") {
        lib.add_source("tamper/unix/tamper.c");
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("tamper/stm32u5/tamper.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
