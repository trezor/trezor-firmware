use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("touch/inc");

    lib.add_define("USE_TOUCH", Some("1"));

    lib.add_source("touch/touch_poll.c");

    if cfg!(feature = "usb_iface_debug") {
        lib.add_source("touch/touch_debug.c");
    }

    if cfg!(feature = "touch_wakeup") {
        if cfg!(not(feature = "suspend")) {
            bail_unsupported!();
        }
        lib.add_define("USE_TOUCH_WAKEUP", Some("1"));
    }

    if cfg!(feature = "emulator") {
        // The emulator reuses the emulated board's touch configuration but always
        // builds the unix driver instead of the HW one. The unix driver does no
        // panel correction, so the selected panel feature is ignored here.
        lib.add_source("touch/unix/touch.c");
    } else if cfg!(feature = "touch_ft3168") {
        add_driver_ft3168(lib)?;
    } else if cfg!(feature = "touch_ft6x36") {
        add_driver_ft6x36(lib)?;
    } else if cfg!(feature = "touch_stmpe811") {
        lib.add_sources(["touch/stmpe811/stmpe811.c", "touch/stmpe811/touch.c"]);
    } else if cfg!(feature = "touch_sitronix") {
        lib.add_sources(["touch/sitronix/touch.c", "touch/sitronix/sitronix.c"]);
    } else {
        bail_unsupported!();
    }

    Ok(())
}

// ---------------------------------------------------------------------------
// Panel functions: panel-selection define only, no driver knowledge.
//
// Only the panel-selection macro lives here; board-specific wiring and tuning
// (TOUCH_SENSITIVITY, reset/interrupt pins, I2C instance) stay in the board
// header.
// -------------------------------------------------------------------------

fn set_panel_t2t1(_lib: &mut CLibrary) {
    // The T2T1 panel needs no touch coordinate correction; the driver falls back
    // to identity mapping when no TOUCH_PANEL_* macro is defined.
}

fn set_panel_lx154a2422cpt23(lib: &mut CLibrary) {
    lib.add_define("TOUCH_PANEL_LX154A2422CPT23", Some("1"));
}

fn set_panel_lx250a2410a(lib: &mut CLibrary) {
    lib.add_define("TOUCH_PANEL_LX250A2410A", Some("1"));
}

// --------------------------------------------------------------------------
// Driver functions: select panel (define + correction source), then add the
// driver sources.
// --------------------------------------------------------------------------

fn add_driver_ft6x36(lib: &mut CLibrary) -> Result<()> {
    lib.add_source("touch/ft6x36/ft6x36.c");
    if cfg!(feature = "touch_panel_t2t1") {
        set_panel_t2t1(lib);
    } else if cfg!(feature = "touch_panel_lx154a2422cpt23") {
        set_panel_lx154a2422cpt23(lib);
        lib.add_source("touch/ft6x36/panels/lx154a2422cpt23.c");
    } else {
        bail_unsupported!();
    }
    Ok(())
}

fn add_driver_ft3168(lib: &mut CLibrary) -> Result<()> {
    lib.add_source("touch/ft3168/ft3168.c");
    if cfg!(feature = "touch_panel_lx250a2410a") {
        set_panel_lx250a2410a(lib);
        lib.add_source("touch/ft3168/panels/lx250a2410a.c");
    } else {
        bail_unsupported!();
    }
    Ok(())
}
