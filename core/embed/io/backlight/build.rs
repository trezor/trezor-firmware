// Defines io/gfx module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("backlight/inc");

    lib.add_public_define("USE_BACKLIGHT", Some("1"));

    if cfg!(feature = "mcu_emulator") {
        return;
    }

    if cfg!(feature = "backlight_tps61043") {
        if cfg!(feature = "mcu_stm32") {
            lib.add_source("backlight/stm32/tps61043.c");
        } else {
            unimplemented!()
        }
    } else if cfg!(feature = "backlight_tps61062") {
        if cfg!(feature = "mcu_stm32u5") {
            lib.add_source("backlight/stm32u5/tps61062.c");
        } else {
            unimplemented!()
        }
    } else {
        unimplemented!();
    }
}
