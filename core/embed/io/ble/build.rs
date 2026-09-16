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

    // Console interface (prodtest CLI, debug console) on its own GATT service
    // and inter-MCU service id; never part of production firmware. The emulator
    // has no nRF and its console is the UDP-backed USB VCP, so the interface
    // does not exist there and consumers fall back to the VCP.
    if cfg!(feature = "ble_console") && !cfg!(feature = "emulator") {
        lib.add_define("USE_BLE_CONSOLE", Some("1"));
        lib.add_sources(["ble/stm32/ble_console.c"]);
    }

    Ok(())
}
