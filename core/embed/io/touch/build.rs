use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("touch/inc");

    lib.add_define("USE_TOUCH", Some("1"));

    lib.add_source("touch/touch_poll.c");

    if cfg!(feature = "usb_iface_debug") {
        lib.add_source("touch/touch_debug.c");
    }

    if cfg!(feature = "emulator") {
        lib.add_source("touch/unix/touch.c");
    } else if cfg!(feature = "touch_ft3168") {
        lib.add_define("TOUCH_WAKEUP_ENABLED", Some("0"));
        lib.add_sources(["touch/ft3168/ft3168.c", "touch/ft3168/panels/lx250a2410a.c"]);
    } else if cfg!(feature = "touch_ft6x36_t3t1") {
        lib.add_sources([
            "touch/ft6x36/ft6x36.c",
            "touch/ft6x36/panels/lx154a2422cpt23.c",
        ]);
    } else if cfg!(feature = "touch_ft6x36_t2t1") {
        lib.add_source("touch/ft6x36/ft6x36.c");
    } else if cfg!(feature = "touch_stmpe811") {
        lib.add_sources([
            "touch/stmpe811/stmpe811.c",
            "touch/stmpe811/touch.c"
        ]);
    } else if cfg!(feature = "touch_sitronix") {
        lib.add_sources([
            "touch/sitronix/touch.c",
            "touch/sitronix/sitronix.c",
        ]);
    } else {
        bail_unsupported!();
    }

    Ok(())
}
