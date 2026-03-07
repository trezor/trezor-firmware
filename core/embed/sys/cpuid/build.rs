// Defines sys/cpuid module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_includes(&["cpuid/inc"]);

    if cfg!(feature = "mcu_stm32") {
        lib.add_source("cpuid/stm32/cpuid.c");
    } else if cfg!(feature = "mcu_emulator") {
        lib.add_source("cpuid/unix/cpuid.c");
    } else {
        unimplemented!();
    }
}
