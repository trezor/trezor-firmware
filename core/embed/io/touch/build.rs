// Defines io/touch module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("touch/inc");

    lib.add_public_defines(&[("USE_TOUCH", Some("1"))]);

    lib.add_source("touch/touch_poll.c");

    if cfg!(feature = "usb_iface_debug") {
        lib.add_source("touch/touch_debug.c");
    }

    if cfg!(feature = "mcu_emulator") {
        lib.add_source("touch/unix/touch.c");
        return;
    }

    if cfg!(feature = "touch_ft6x36_t3t1") {
        lib.add_sources(&["touch/ft3168/ft3168.c", "touch/ft3168/panels/lx250a2410a.c"]);
    } else if cfg!(feature = "touch_ft6x36_t3t1") {
        lib.add_sources(&[
            "touch/ft6x36/ft6x36.c",
            "touch/ft6x36/panels/lx154a2422cpt23.c",
        ]);
    } else if cfg!(feature = "touch_ft6x36_t2t1") {
        lib.add_sources(&["touch/ft6x36/ft6x36.c"]);
    } else {
        unimplemented!();
    }
}
