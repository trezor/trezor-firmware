// Defines io/haptic module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("haptic/inc");

    lib.add_public_define("USE_HAPTIC", Some("1"));

    if cfg!(feature = "mcu_stm32") {
        lib.add_source("haptic/drv262x/drv262x.c");
    } else if cfg!(feature = "mcu_emulator") {
        // No haptic support in emulator
    } else {
        unimplemented!();
    }
}
