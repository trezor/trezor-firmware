use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("display/inc");

    lib.add_define("USE_DISPLAY", Some("1"));

    if cfg!(feature = "emulator") && cfg!(feature = "raspi_emulator") {
        lib.add_define("TREZOR_EMULATOR_RASPI", Some("1"));
    }

    lib.add_source("display/display_utils.c");

    if cfg!(feature = "mcu_stm32f4") {
        lib.add_source("display/stm32f4/compatibility.c");
    }

    if cfg!(feature = "framebuffer") {
        lib.add_define("FRAMEBUFFER", Some("1"));
    }

    if cfg!(feature = "display_unix") {
        add_driver_unix(lib)?;
    } else if cfg!(feature = "display_ltdc_dsi") {
        add_driver_ltdc_dsi(lib)?;
    } else if cfg!(feature = "display_st7789") {
        add_driver_st7789(lib)?;
    } else if cfg!(feature = "display_vg2864") {
        add_driver_vg2864(lib)?;
    } else if cfg!(feature = "display_stm32f429i_disc1") {
        add_driver_stm32f429i_disc1(lib)?;
    } else {
        bail_unsupported!();
    }

    Ok(())
}

// --------------------------------------------------------------------------
// Panel functions: defines only, no sources, no driver knowledge
// --------------------------------------------------------------------------

fn set_panel_lx250a2401a(lib: &mut CLibrary) {
    lib.add_defines([
        ("UI_COLOR_32BIT", Some("1")),
        ("USE_RGB_COLORS", Some("1")),
        ("DISPLAY_RESX", Some("380")),
        ("DISPLAY_RESY", Some("520")),
        ("TERMINAL_FONT_SCALE", Some("2")),
        ("TERMINAL_X_PADDING", Some("4")),
        ("TERMINAL_Y_PADDING", Some("12")),
    ]);
}

fn set_panel_stm32u5a9j_dk(lib: &mut CLibrary) {
    lib.add_defines([
        ("UI_COLOR_32BIT", Some("1")),
        ("USE_RGB_COLORS", Some("1")),
        ("DISPLAY_RESX", Some("240")),
        ("DISPLAY_RESY", Some("240")),
    ]);
}

fn set_panel_lx154a2482(lib: &mut CLibrary) {
    lib.add_defines([
        ("USE_RGB_COLORS", Some("1")),
        ("DISPLAY_RESX", Some("240")),
        ("DISPLAY_RESY", Some("240")),
    ]);
}

fn set_panel_t2t1(lib: &mut CLibrary) {
    lib.add_defines([
        ("USE_RGB_COLORS", Some("1")),
        ("DISPLAY_RESX", Some("240")),
        ("DISPLAY_RESY", Some("240")),
    ]);
}

fn set_panel_vg2864(lib: &mut CLibrary) {
    lib.add_defines([
        ("DISPLAY_RESX", Some("128")),
        ("DISPLAY_RESY", Some("64")),
    ]);
    lib.add_private_define("DISPLAY_MONO", Some("1"));
}

// --------------------------------------------------------------------------
// Driver functions: select panel (defines), then add sources
// --------------------------------------------------------------------------

fn add_driver_unix(lib: &mut CLibrary) -> Result<()> {
    if cfg!(feature = "display_panel_lx250a2401a") {
        set_panel_lx250a2401a(lib);
    } else if cfg!(feature = "display_panel_stm32u5a9j_dk") {
        set_panel_stm32u5a9j_dk(lib);
    } else if cfg!(feature = "display_panel_lx154a2482") {
        set_panel_lx154a2482(lib);
    } else if cfg!(feature = "display_panel_t2t1") {
        set_panel_t2t1(lib);
    } else if cfg!(feature = "display_panel_vg2864") {
        set_panel_vg2864(lib);
    } else {
        bail_unsupported!();
    }
    lib.add_source("display/unix/display_driver.c");
    Ok(())
}

fn add_driver_ltdc_dsi(lib: &mut CLibrary) -> Result<()> {
    if cfg!(feature = "mcu_stm32u5g") {
        lib.add_sources([
            "display/ltdc_dsi/display_driver.c",
            "display/ltdc_dsi/display_fb.c",
            "display/ltdc_dsi/display_fb_rgb888.c",
            "display/fb_queue/fb_queue.c",
        ]);
        if cfg!(feature = "display_panel_lx250a2401a") {
            set_panel_lx250a2401a(lib);
            lib.add_sources([
                "display/ltdc_dsi/panels/lx250a2401a/lx250a2401a.c",
                "display/ltdc_dsi/display_gfxmmu.c",
            ]);
        } else if cfg!(feature = "display_panel_stm32u5a9j_dk") {
            set_panel_stm32u5a9j_dk(lib);
            lib.add_source("display/ltdc_dsi/panels/stm32u5a9j-dk/stm32u5a9j-dk.c");
        } else {
            bail_unsupported!();
        }
    } else {
        bail_unsupported!();
    }
    Ok(())
}

fn add_driver_st7789(lib: &mut CLibrary) -> Result<()> {
    if cfg!(feature = "mcu_stm32u58") {
        lib.add_sources([
            "display/st-7789/display_driver.c",
            "display/st-7789/display_io.c",
            "display/st-7789/display_panel.c",
        ]);
        if cfg!(feature = "display_panel_lx154a2482") {
            set_panel_lx154a2482(lib);
            lib.add_source("display/st-7789/panels/lx154a2482.c");
        } else {
            bail_unsupported!();
        }
        if cfg!(feature = "framebuffer") {
            lib.add_sources([
                "display/bg_copy/stm32u5/bg_copy.c",
                "display/fb_queue/fb_queue.c",
                "display/st-7789/display_fb.c",
            ]);
        } else {
            lib.add_source("display/st-7789/display_nofb.c");
        }
    } else if cfg!(feature = "mcu_stm32f4") {
        lib.add_sources([
            "display/st-7789/display_nofb.c",
            "display/st-7789/display_driver.c",
            "display/st-7789/display_io.c",
            "display/st-7789/display_panel.c",
        ]);
        if cfg!(feature = "display_panel_t2t1") {
            set_panel_t2t1(lib);
            lib.add_sources([
                "display/st-7789/panels/t2t1.c",
                "display/st-7789/panels/tf15411a.c",
                "display/st-7789/panels/154a.c",
                "display/st-7789/panels/lx154a2411.c",
                "display/st-7789/panels/lx154a2422.c",
            ]);
        } else {
            bail_unsupported!();
        }
    } else {
        bail_unsupported!();
    }
    Ok(())
}

fn add_driver_vg2864(lib: &mut CLibrary) -> Result<()> {
    if cfg!(feature = "display_panel_vg2864") {
        set_panel_vg2864(lib);
    } else {
        bail_unsupported!();
    }
    if cfg!(feature = "mcu_stm32u58") || cfg!(feature = "mcu_stm32f4") {
        lib.add_source("display/vg-2864/display_driver.c");
    } else {
        bail_unsupported!();
    }
    Ok(())
}

fn add_driver_stm32f429i_disc1(lib: &mut CLibrary) -> Result<()> {
    lib.add_defines([
        ("USE_RGB_COLORS", Some("1")),
        ("DISPLAY_RESX", Some("240")),
        ("DISPLAY_RESY", Some("320")),
    ]);
    if cfg!(feature = "mcu_stm32f4") {
        lib.add_sources([
            "display/stm32f429i-disc1/display_driver.c",
            "display/stm32f429i-disc1/display_ltdc.c",
            "display/stm32f429i-disc1/ili9341_spi.c",
        ]);
    } else {
        bail_unsupported!();
    }
    Ok(())
}
