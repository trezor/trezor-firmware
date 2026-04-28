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

    if cfg!(feature = "model_t3w1") {
        define_display_t3w1(lib)?;
    } else if cfg!(feature = "model_t3t1") {
        define_display_t3t1(lib)?;
    } else if cfg!(feature = "model_t2t1") {
        define_display_t2t1(lib)?;
    } else if cfg!(feature = "model_t2b1") || cfg!(feature = "model_t3b1") {
        define_display_t2b1_t3b1(lib)?;
    } else if cfg!(feature = "model_d001") {
        define_display_d001(lib)?;
    } else if cfg!(feature = "model_d002") {
        define_display_d002(lib)?;
    } else {
        bail_unsupported!();
    }

    Ok(())
}

fn define_display_t3w1(lib: &mut CLibrary) -> Result<()> {
    lib.add_defines([
        ("UI_COLOR_32BIT", Some("1")),
        ("FRAMEBUFFER", Some("1")),
        ("USE_RGB_COLORS", Some("1")),
        ("DISPLAY_RESX", Some("380")),
        ("DISPLAY_RESY", Some("520")),
        ("TERMINAL_FONT_SCALE", Some("2")),
        ("TERMINAL_X_PADDING", Some("4")),
        ("TERMINAL_Y_PADDING", Some("12")),
    ]);

    if cfg!(feature = "emulator") {
        lib.add_source("display/unix/display_driver.c");
    } else if cfg!(feature = "mcu_stm32u5g") {
        lib.add_sources([
            "display/ltdc_dsi/display_driver.c",
            "display/ltdc_dsi/panels/lx250a2401a/lx250a2401a.c",
            "display/ltdc_dsi/display_fb.c",
            "display/ltdc_dsi/display_fb_rgb888.c",
            "display/ltdc_dsi/display_gfxmmu.c",
            "display/fb_queue/fb_queue.c",
        ]);
    } else {
        bail_unsupported!();
    }
    Ok(())
}

fn define_display_t3t1(lib: &mut CLibrary) -> Result<()> {
    lib.add_defines([
        ("FRAMEBUFFER", Some("1")),
        ("USE_RGB_COLORS", Some("1")),
        ("DISPLAY_RESX", Some("240")),
        ("DISPLAY_RESY", Some("240")),
    ]);

    if cfg!(feature = "emulator") {
        lib.add_source("display/unix/display_driver.c");
    } else if cfg!(feature = "mcu_stm32u58") {
        lib.add_sources([
            "display/bg_copy/stm32u5/bg_copy.c",
            "display/fb_queue/fb_queue.c",
            "display/st-7789/display_driver.c",
            "display/st-7789/display_fb.c",
            "display/st-7789/display_io.c",
            "display/st-7789/display_panel.c",
            "display/st-7789/panels/lx154a2482.c",
        ]);
    } else {
        bail_unsupported!();
    }
    Ok(())
}

fn define_display_t2t1(lib: &mut CLibrary) -> Result<()> {
    lib.add_defines([
        ("USE_RGB_COLORS", Some("1")),
        ("DISPLAY_RESX", Some("240")),
        ("DISPLAY_RESY", Some("240")),
    ]);

    if cfg!(feature = "emulator") {
        lib.add_source("display/unix/display_driver.c");
    } else if cfg!(feature = "mcu_stm32f4") {
        lib.add_sources([
            "display/st-7789/display_nofb.c",
            "display/st-7789/display_driver.c",
            "display/st-7789/display_io.c",
            "display/st-7789/display_panel.c",
            "display/st-7789/panels/tf15411a.c",
            "display/st-7789/panels/154a.c",
            "display/st-7789/panels/lx154a2411.c",
            "display/st-7789/panels/lx154a2422.c",
        ]);
    } else {
        bail_unsupported!();
    }
    Ok(())
}

fn define_display_t2b1_t3b1(lib: &mut CLibrary) -> Result<()> {
    lib.add_defines([
        ("FRAMEBUFFER", Some("1")),
        ("DISPLAY_RESX", Some("128")),
        ("DISPLAY_RESY", Some("64")),
    ]);

    if cfg!(feature = "emulator") {
        lib.add_private_define("DISPLAY_MONO", Some("1"));
        lib.add_source("display/unix/display_driver.c");
    } else if cfg!(feature = "mcu_stm32u58") || cfg!(feature = "mcu_stm32f4") {
        lib.add_source("display/vg-2864/display_driver.c");
    } else {
        bail_unsupported!();
    }
    Ok(())
}

fn define_display_d001(lib: &mut CLibrary) -> Result<()> {
    lib.add_defines([
        ("FRAMEBUFFER", Some("1")),
        ("USE_RGB_COLORS", Some("1")),
        ("DISPLAY_RESX", Some("240")),
        ("DISPLAY_RESY", Some("320")),
    ]);

    if cfg!(feature = "emulator") {
        lib.add_source("display/unix/display_driver.c");
    } else if cfg!(feature = "mcu_stm32f4") {
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

fn define_display_d002(lib: &mut CLibrary) -> Result<()> {
    lib.add_defines([
        ("FRAMEBUFFER", Some("1")),
        ("UI_COLOR_32BIT", Some("1")),
        ("USE_RGB_COLORS", Some("1")),
        ("DISPLAY_RESX", Some("240")),
        ("DISPLAY_RESY", Some("240")),
    ]);

    if cfg!(feature = "emulator") {
        lib.add_source("display/unix/display_driver.c");
    } else if cfg!(feature = "mcu_stm32u5g") {
        lib.add_sources([
            "display/ltdc_dsi/display_driver.c",
            "display/ltdc_dsi/panels/stm32u5a9j-dk/stm32u5a9j-dk.c",
            "display/ltdc_dsi/display_fb.c",
            "display/ltdc_dsi/display_fb_rgb888.c",
            "display/fb_queue/fb_queue.c",
        ]);
    } else {
        bail_unsupported!();
    }
    Ok(())
}
