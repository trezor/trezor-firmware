use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("rgb_led/inc");

    lib.add_define("USE_RGB_LED", Some("1"));

    if cfg!(feature = "emulator") {
        lib.add_source("rgb_led/unix/rgb_led.c");
    } else if cfg!(feature = "mcu_stm32f4") {
        // TODO: do we really need this??
        lib.add_source("rgb_led/stm32/rgb_led.c");
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("rgb_led/stm32u5/rgb_led_lp.c");
        lib.add_source("rgb_led/stm32u5/rgb_led_effects.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
