// Defines sec/board_capabilities module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("board_capabilities/inc");

    if cfg!(feature = "mcu_stm32") {
        lib.add_source("board_capabilities/stm32/board_capabilities.c");
    } else if cfg!(feature = "mcu_emulator") {
        lib.add_source("board_capabilities/unix/board_capabilities.c");
    } else {
        unimplemented!();
    }
}
