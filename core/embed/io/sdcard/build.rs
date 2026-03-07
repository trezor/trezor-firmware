// Defines io/sdcard module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("sdcard/inc");

    lib.add_public_define("USE_SD_CARD", Some("1"));

    if cfg!(feature = "mcu_stm32f4") {
        lib.add_source("sdcard/stm32f4/sdcard.c");
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("sdcard/stm32u5/sdcard.c");
    } else if cfg!(feature = "mcu_emulator") {
        lib.add_source("sdcard/unix/sdcard.c");
    } else {
        unimplemented!()
    }

    // TODO!@# What's this????
    // sources += ["embed/upymod/modtrezorio/ff.c"]
    // sources += ["embed/upymod/modtrezorio/ffunicode.c"]
}
