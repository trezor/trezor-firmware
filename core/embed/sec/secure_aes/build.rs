// Define sec/secure_aes module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("secure_aes/inc");

    if cfg!(feature = "mcu_emulator") {
        return;
    }

    if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("secure_aes/stm32u5/secure_aes.c");
        lib.add_source("secure_aes/stm32u5/secure_aes_unpriv.c");
    } else {
        unimplemented!();
    }
}
