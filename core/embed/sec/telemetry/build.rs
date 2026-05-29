use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("telemetry/inc");

    lib.add_define("USE_TELEMETRY", Some("1"));

    if cfg!(feature = "emulator") {
        lib.add_source("telemetry/unix/telemetry.c");
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("telemetry/stm32u5/telemetry.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
