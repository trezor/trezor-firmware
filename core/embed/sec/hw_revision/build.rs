// Defines sec/hw_revision module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("hw_revision/inc");

    lib.add_public_define("USE_HW_REVISION", Some("1"));

    if cfg!(feature = "mcu_stm32") {
        lib.add_source("hw_revision/stm32/hw_revision.c");
    } else {
        unimplemented!();
    }
}
