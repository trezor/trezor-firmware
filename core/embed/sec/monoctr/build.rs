// Define sec/monoctr module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("monoctr/inc");

    if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("monoctr/stm32u5/monoctr.c");
    } else if cfg!(feature = "mcu_stm32f4") {
        lib.add_source("monoctr/stm32f4/monoctr.c");
    } else if cfg!(feature = "mcu_emulator") {
        lib.add_source("monoctr/unix/monoctr.c");
    } else {
        unimplemented!();
    }
}
