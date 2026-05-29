use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("button/inc");

    lib.add_define("USE_BUTTON", Some("1"));

    lib.add_source("button/button_poll.c");

    if cfg!(feature = "usb_iface_debug") {
        lib.add_source("button/button_debug.c");
    }

    if cfg!(feature = "emulator") {
        lib.add_source("button/unix/button.c");
    } else if cfg!(feature = "mcu_stm32") {
        lib.add_source("button/stm32/button.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
