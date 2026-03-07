// Defines io/power_manager module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("power_manager/inc");

    lib.add_public_define("USE_PMIC", Some("1"));

    if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("power_manager/npm1300/npm1300.c");
    } else if cfg!(feature = "mcu_emulator") {
        // No sources
    } else {
        unimplemented!();
    }

    if !cfg!(feature = "power_manager") {
        // if only PMIC is needed, we don't need the rest of
        //the power manager sources
        return;
    }

    lib.add_public_define("USE_POWER_MANAGER", Some("1"));

    lib.add_source("power_manager/power_manager_poll.c");

    if cfg!(feature = "mcu_emulator") {
        lib.add_source("power_manager/unix/power_manager.c");
        return;
    }

    if cfg!(feature = "mcu_stm32u5") {
        lib.add_sources(&[
            "power_manager/stm32u5/power_manager.c",
            "power_manager/stm32u5/power_monitoring.c",
            "power_manager/stm32u5/power_states.c",
            "power_manager/battery/battery.c",
            "power_manager/battery/fuel_gauge.c",
            "power_manager/battery/battery_model.c",
            "power_manager/stwlc38/stwlc38.c",
            "power_manager/stwlc38/stwlc38_patching.c",
            "power_manager/power_manager_poll.c",
        ]);
    } else {
        unimplemented!();
    }
}
