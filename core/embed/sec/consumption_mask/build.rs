// Defines sec/consumption_mask module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("consumption_mask/inc");

    lib.add_public_define("USE_CONSUMPTION_MASK", Some("1"));

    if cfg!(feature = "mcu_emulator") {
        return;
    }

    if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("consumption_mask/stm32u5/consumption_mask.c");
    } else if cfg!(feature = "mcu_stm32f4") {
        lib.add_source("consumption_mask/stm32f4/consumption_mask.c");
    } else {
        unimplemented!();
    }
}
