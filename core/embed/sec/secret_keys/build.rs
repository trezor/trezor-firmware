// Defines sec/secret_keys module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("secret_keys/inc");

    lib.add_public_define("USE_SECRET_KEYS", Some("1"));

    if cfg!(feature = "mcu_stm32f4") {
        lib.add_source("secret_keys/stm32f4/secret_keys.c");
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("secret_keys/stm32u5/secret_keys.c");
    } else if cfg!(feature = "mcu_emulator") {
        lib.add_source("secret_keys/unix/secret_keys.c");
    } else {
        unimplemented!();
    }

    lib.add_source("secret_keys/secret_keys_common.c")
}
