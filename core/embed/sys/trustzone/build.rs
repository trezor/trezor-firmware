// Defines sec/rng module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("trustzone/inc");

    if cfg!(feature = "mcu_stm32") {
        lib.add_source("trustzone/stm32u5/trustzone.c");
    } else {
        unimplemented!();
    }
}
