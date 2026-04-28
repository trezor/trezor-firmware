use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("storage/inc");

    lib.add_define("USE_STORAGE", Some("1"));

    if cfg!(not(feature = "secure_mode")) {
        // TODO: refactor to avoid this hack
        // Storage source code doe not contain #ifdef SECURE_MODE,
        // so we need to exclude it entirely in non-secure mode
        return Ok(());
    }

    if cfg!(feature = "storage_insecure_testing_mode") {
        lib.add_define("STORAGE_INSECURE_TESTING_MODE", Some("1"));
    }

    lib.add_source("storage/storage_setup.c");

    lib.add_sources_from_folder(
        "../../vendor/trezor-storage/",
        ["norcow.c", "storage.c", "storage_utils.c"],
    );

    if cfg!(feature = "emulator") {
        lib.add_source("storage/unix/storage_salt.c");
    } else if cfg!(feature = "mcu_stm32f4") {
        lib.add_source("storage/stm32f4/storage_salt.c");
        if cfg!(feature = "storage_hw_key") {
            bail_unsupported!();
        }
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("storage/stm32u5/storage_salt.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
