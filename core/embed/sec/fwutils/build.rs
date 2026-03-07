// Defines sec/fwutils module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("fwutils/inc");

    if cfg!(feature = "mcu_emulator") {
        return;
    }

    lib.add_source("fwutils/fwutils.c");
}
