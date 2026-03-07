// Defines sec/storage module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("storage/inc");

    lib.add_public_define("USE_STORAGE", Some("1"));

    if !cfg!(feature = "secure_mode") {
        // !@# temp hack??
        // Storage source code doe not contain #ifdef SECURE_MODE,
        // so we need to exclude it entirely in non-secure mode
        return;
    }

    if cfg!(feature = "mcu_stm32f4") {
        lib.add_source("storage/stm32f4/storage_salt.c");
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("storage/stm32u5/storage_salt.c");
    } else if cfg!(feature = "mcu_emulator") {
        lib.add_source("storage/unix/storage_salt.c");
    } else {
        unimplemented!();
    }

    lib.add_source("storage/storage_setup.c");

    lib.add_sources_from_folder(
        "../../vendor/trezor-storage/",
        &["norcow.c", "storage.c", "storage_utils.c"],
    );
}
