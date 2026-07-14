use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("power_manager/inc");
    // power_manager.h pulls in <io/suspend.h> for wakeup_flags_t; make that
    // header reachable even on boards that don't compile the suspend module.
    lib.add_include("suspend/inc");

    let latch = cfg!(feature = "pmic_power_latch");

    // --- PMIC driver (low-level power IC / power switch) -------------------
    if cfg!(feature = "pmic") {
        lib.add_define("USE_PMIC", Some("1"));
    }

    if cfg!(feature = "emulator") {
        // No PMIC implementation in the emulator.
    } else if cfg!(feature = "mcu_stm32u5") {
        if latch {
            lib.add_source("power_manager/power_latch/power_latch.c");
        } else if cfg!(feature = "pmic_npm1300") {
            lib.add_source("power_manager/npm1300/npm1300.c");
        }
    } else if cfg!(any(feature = "pmic_npm1300", feature = "pmic_power_latch")) {
        bail_unsupported!();
    }

    if cfg!(not(feature = "power_manager")) {
        // Boardloader and similar only need the PMIC driver, not the rest of
        // the power manager.
        return Ok(());
    }

    lib.add_define("USE_POWER_MANAGER", Some("1"));
    lib.add_source("power_manager/power_manager_poll.c");

    // --- Optional wireless charger ----------------------------------------
    if cfg!(feature = "wireless_stwlc38") {
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
    } else if latch {
        // Minimal backend for boards whose only power hardware is the latch.
        lib.add_source("power_manager/power_latch/power_manager.c");
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_sources([
            "power_manager/npm1300/power_manager.c",
            "power_manager/npm1300/power_monitoring.c",
            "power_manager/npm1300/power_states.c",
            "power_manager/battery/battery.c",
            "power_manager/battery/fuel_gauge.c",
            "power_manager/battery/battery_model.c",
        ]);
    } else {
        bail_unsupported!();
    }

    Ok(())
}
