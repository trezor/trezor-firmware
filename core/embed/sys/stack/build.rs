// Defines sys/stack module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("stack/inc");

    if cfg!(feature = "mcu_emulator") {
        return;
    }

    if cfg!(feature = "mcu_stm32") {
        lib.add_source("stack/stm32/stack_utils.c");
    } else {
        unimplemented!();
    }
}
