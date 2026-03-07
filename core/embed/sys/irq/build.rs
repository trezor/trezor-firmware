// Defines sys/irq module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_includes(&["irq/inc"]);

    if cfg!(feature = "mcu_stm32") {
        lib.add_sources(&["irq/stm32/irq.c"]);
    } else if cfg!(feature = "mcu_emulator") {
        // No sources
    } else {
        unimplemented!();
    }
}
