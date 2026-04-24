use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("ble/inc");

    lib.add_define("USE_BLE", Some("1"));

    if cfg!(feature = "emulator") {
        lib.add_sources(["ble/unix/ble.c"]);
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_sources(["ble/stm32/ble.c"]);
    } else {
        bail_unsupported!();
    }

    Ok(())
}
