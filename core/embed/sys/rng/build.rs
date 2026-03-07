// Defines sys/rng module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_includes(&["rng/inc"]);

    if cfg!(feature = "mcu_stm32") {
        lib.add_sources(&["rng/stm32/rng.c"]);
    } else if cfg!(feature = "mcu_emulator") {
        lib.add_sources(&["rng/unix/rng.c"]);
    } else {
        unimplemented!();
    }
}
