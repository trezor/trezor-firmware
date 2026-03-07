// Defines io/button module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("button/inc");

    lib.add_public_define("USE_BUTTON", Some("1"));

    if cfg!(feature = "mcu_stm32") {
        lib.add_source("button/stm32/button.c");
    } else if cfg!(feature = "mcu_emulator") {
        lib.add_source("button/unix/button.c");
    } else {
        unimplemented!();
    }

    if cfg!(feature = "usb_iface_debug") {
        lib.add_source("button/button_debug.c");
    }

    lib.add_sources(&["button/button_poll.c"]);
}
