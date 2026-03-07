// Defines sec/hash_processor module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("hash_processor/inc");

    lib.add_public_define("USE_HASH_PROCESSOR", Some("1"));

    if cfg!(feature = "mcu_emulator") {
        return;
    }

    if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("hash_processor/stm32u5/hash_processor.c");
    } else {
        unimplemented!();
    }
}
