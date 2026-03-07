// Defines sec/iwdg module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("iwdg/inc");

    lib.add_public_define("USE_IWDG", Some("1"));

    if cfg!(feature = "mcu_stm32") {
        lib.add_source("iwdg/stm32/iwdg.c");
    } else {
        unimplemented!();
    }
}
