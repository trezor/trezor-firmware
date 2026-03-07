// Define sec/suspend module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("suspend/inc");

    lib.add_public_define("USE_SUSPEND", Some("1"));

    if cfg!(feature = "mcu_emulator") {
        return;
    }

    if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("suspend/stm32u5/suspend_io.c");
    } else {
        unimplemented!();
    }
}
