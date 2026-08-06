use xbuild::{CLibrary, Result, bail_unsupported, ensure};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("power_manager/inc");
    // power_manager.h pulls in <io/suspend.h> for wakeup_flags_t; make that
    // header reachable even on boards that don't compile the suspend module.
    lib.add_include("suspend/inc");

    // --- PMIC driver (low-level power IC) ---------------------------------
    // Handled before the power_manager early-return below, because pmic-only
    // builds (e.g. the boardloader) need the driver without the full backend.
    // The board selects a concrete driver via the `[power_manager]` peripheral
    // `pmic = "io/pmic_..."` specifier.
    //
    // Selection is a table + "exactly one" check rather than a chain of
    // independent `if`s, so a mis-mapped or duplicate feature is a clear build
    // error instead of two drivers compiling into duplicate symbols.
    if cfg!(feature = "pmic") {
        lib.add_define("USE_PMIC", Some("1"));

        // (feature name, hardware source) for each enabled concrete PMIC
        // driver. A new driver adds its own arm here.
        let mut drivers: Vec<(&str, &str)> = Vec::new();
        if cfg!(feature = "pmic_npm1300") {
            drivers.push(("pmic_npm1300", "power_manager/pmic/npm1300/npm1300.c"));
        }

        ensure!(
            drivers.len() == 1,
            "power_manager: exactly one PMIC driver must be selected \
             (set `pmic = \"io/pmic_...\"` in the board's [power_manager] \
             section), found {}: {:?}",
            drivers.len(),
            drivers.iter().map(|(f, _)| *f).collect::<Vec<_>>()
        );
        let (_feature, source) = drivers[0];

        // The concrete PMIC drivers are STM32U5 parts with no emulator build.
        if cfg!(feature = "emulator") {
            // no hardware PMIC in the emulator
        } else if cfg!(feature = "mcu_stm32u5") {
            lib.add_source(source);
        } else {
            bail_unsupported!();
        }

        // Charger capability of the selected PMIC. Gates the `managed` policy's
        // charging controller (see USE_CHARGER in power_monitoring.c). npm1300
        // has an integrated charger; a chargerless PMIC (npm2100, a bare GPIO
        // power latch) simply doesn't define it.
        if cfg!(feature = "pmic_npm1300") {
            lib.add_define("USE_CHARGER", Some("1"));
        }
    }

    if cfg!(not(feature = "power_manager")) {
        // Boardloader and similar only need the PMIC driver, not the rest of
        // the power manager.
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
                "power_manager/wireless/stwlc38/stwlc38.c",
                "power_manager/wireless/stwlc38/stwlc38_patching.c",
            ]);
        }
    }

    // --- Power manager backend --------------------------------------------
    // There is a single hardware policy - `managed` - for every PMIC. It
    // implements power_manager.h on top of the core PMIC interface and gates
    // charger-only logic behind USE_CHARGER (set above per PMIC capability).
    // A latch board simply runs `managed` with USE_CHARGER off.
    //
    // There is therefore no per-backend feature: the board selects only a PMIC
    // (`pmic = "io/pmic_..."`), and the project opting into `power_manager`
    // (this point in the code) is enough to build the policy on top of it. The
    // only requirement is that a PMIC driver was actually selected.
    //
    // The emulator is a special case: it reimplements power_manager.h on the
    // host (SDL) and takes precedence over whatever hardware backend the model
    // nominally enables.
    if cfg!(feature = "emulator") {
        lib.add_source("power_manager/unix/power_manager.c");
    } else {
        ensure!(
            cfg!(feature = "pmic"),
            "power_manager: a PMIC driver must be selected \
             (set `pmic = \"io/pmic_...\"` in the board's [power_manager] section)"
        );
        lib.add_sources([
            "power_manager/managed/power_manager.c",
            "power_manager/managed/power_monitoring.c",
            "power_manager/managed/power_states.c",
        ]);

        // Fuel gauge (SoC estimator). The `managed` policy speaks only to the
        // chemistry-neutral fuel_gauge/battery.h interface; the board picks a
        // concrete implementation via `fuel_gauge = "io/fuel_gauge_..."`, an axis
        // mirroring the PMIC selector above. LiFePO4 is the only impl today.
        ensure!(
            cfg!(feature = "fuel_gauge_lifepo4"),
            "power_manager: a fuel gauge must be selected \
             (set `fuel_gauge = \"io/fuel_gauge_lifepo4\"` in the board's \
             [power_manager] section)"
        );
        lib.add_sources([
            "power_manager/fuel_gauge/lifepo4/battery.c",
            "power_manager/fuel_gauge/lifepo4/fuel_gauge.c",
            "power_manager/fuel_gauge/lifepo4/battery_model.c",
        ]);
    }

    Ok(())
}
