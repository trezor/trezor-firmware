use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("power_manager/inc");

    lib.add_define("USE_PMIC", Some("1"));

    if cfg!(feature = "emulator") {
        // No implementation
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("power_manager/npm1300/npm1300.c");
    } else {
        bail_unsupported!();
    }

    if cfg!(not(feature = "power_manager")) {
        // if only PMIC is needed, we don't need the rest of
        //the power manager sources
        return Ok(());
    }

    lib.add_define("USE_POWER_MANAGER", Some("1"));

    lib.add_source("power_manager/power_manager_poll.c");

    // --- Optional wireless charger ----------------------------------------
    // Not present in the emulator (the STWLC38 driver needs the STM32 HAL).
    if cfg!(feature = "wireless_stwlc38") && cfg!(not(feature = "emulator")) {
        lib.add_define("USE_WIRELESS_CHARGER", Some("1"));
        if cfg!(feature = "mcu_stm32u5") {
            lib.add_sources([
                "power_manager/stwlc38/stwlc38.c",
                "power_manager/stwlc38/stwlc38_patching.c",
            ]);
        }
    }

    // --- Power manager backend --------------------------------------------
    if cfg!(feature = "emulator") {
        lib.add_source("power_manager/unix/power_manager.c");
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_sources([
            "power_manager/stm32u5/power_manager.c",
            "power_manager/stm32u5/power_monitoring.c",
            "power_manager/stm32u5/power_states.c",
            "power_manager/battery/battery.c",
            "power_manager/battery/fuel_gauge.c",
            "power_manager/battery/battery_model.c",
        ]);
    } else {
        bail_unsupported!();
    }

    Ok(())
}
