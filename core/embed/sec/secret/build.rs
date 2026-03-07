// Defines sec/secret module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("secret/inc");

    lib.add_public_define("USE_SECRET", Some("1"));

    if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("secret/stm32u5/secret.c");
    } else if cfg!(feature = "mcu_stm32f4") {
        lib.add_source("secret/stm32f4/secret.c");
    } else if cfg!(feature = "mcu_emulator") {
        lib.add_source("secret/unix/secret.c");
    } else {
        unimplemented!();
    }
}
