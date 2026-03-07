// Defines io/sbu module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("sbu/inc");

    lib.add_public_define("USE_SBU", Some("1"));

    if cfg!(feature = "mcu_stm32") {
        lib.add_source("sbu/stm32/sbu.c");
    } else if cfg!(feature = "mcu_emulator") {
        lib.add_source("sbu/unix/sbu.c");
    } else {
        unimplemented!()
    }
}
