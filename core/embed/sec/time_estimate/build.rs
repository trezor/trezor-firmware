// Defines sec/time_estimate module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("time_estimate/inc");

    if cfg!(feature = "mcu_stm32") {
        lib.add_source("time_estimate/stm32/time_estimate.c");
    } else if cfg!(feature = "mcu_emulator") {
        lib.add_source("time_estimate/unix/time_estimate.c");
    } else {
        unimplemented!();
    }
}
