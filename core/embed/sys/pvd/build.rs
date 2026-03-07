// Defines sys/pvd module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_includes(&["pvd/inc"]);

    lib.add_public_define("USE_PVD", Some("1"));

    if cfg!(feature = "mcu_emulator") {
        return;
    }

    if cfg!(feature = "mcu_stm32") {
        lib.add_source("pvd/stm32/pvd.c");
    } else {
        unimplemented!();
    }
}
