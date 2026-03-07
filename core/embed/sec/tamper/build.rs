// Defines sec/tamper module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("tamper/inc");

    lib.add_public_define("USE_TAMPER", Some("1"));

    if cfg!(feature = "mcu_emulator") {
        return;
    }

    if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("tamper/stm32u5/tamper.c");
    } else {
        unimplemented!();
    }
}
