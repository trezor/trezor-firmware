// Defines sec/option_bytes module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("option_bytes/inc");

    if cfg!(feature = "mcu_emulator") {
        return;
    }

    if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("option_bytes/stm32u5/option_bytes.c");
    } else if cfg!(feature = "mcu_stm32f4") {
        lib.add_source("option_bytes/stm32f4/option_bytes.c");
    } else {
        unimplemented!();
    }
}
