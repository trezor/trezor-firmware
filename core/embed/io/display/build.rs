// Defines io/display module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("display/inc");

    lib.add_public_defines(&[("USE_DISPLAY", Some("1"))]);

    lib.add_source("display/display_utils.c");

    if cfg!(feature = "model_t3w1") {
        if cfg!(feature = "mcu_stm32u5g") {
            lib.add_sources(&[
                "display/ltdc_dsi/display_driver.c",
                "display/ltdc_dsi/panels/lx250a2401a/lx250a2401a.c",
                "display/ltdc_dsi/display_fb.c",
                "display/ltdc_dsi/display_fb_rgb888.c",
                "display/ltdc_dsi/display_gfxmmu.c",
                "display/fb_queue/fb_queue.c",
            ]);
        } else if cfg!(feature = "mcu_emulator") {
            lib.add_source("display/unix/display_driver.c");
        } else {
            unimplemented!()
        }

        lib.add_public_defines(&[
            ("DISPLAY_RGBA8888", Some("1")),
            ("UI_COLOR_32BIT", Some("1")),
            ("FRAMEBUFFER", Some("1")),
            ("USE_RGB_COLORS", Some("1")),
            ("DISPLAY_RESX", Some("380")),
            ("DISPLAY_RESY", Some("520")),
            ("TERMINAL_FONT_SCALE", Some("2")),
            ("TERMINAL_X_PADDING", Some("4")),
            ("TERMINAL_Y_PADDING", Some("12")),
        ]);
    } else if cfg!(feature = "model_t3t1") {
        if cfg!(feature = "mcu_stm32u58") {
            lib.add_sources(&[
                "display/bg_copy/stm32u5/bg_copy.c",
                "display/fb_queue/fb_queue.c",
                "display/st-7789/display_driver.c",
                "display/st-7789/display_fb.c",
                "display/st-7789/display_io.c",
                "display/st-7789/display_panel.c",
                "display/st-7789/panels/lx154a2482.c",
            ]);
        } else if cfg!(feature = "mcu_emulator") {
            lib.add_source("display/unix/display_driver.c");
        } else {
            unimplemented!()
        }

        lib.add_public_defines(&[
            ("DISPLAY_RGB565", Some("1")),
            ("FRAMEBUFFER", Some("1")),
            ("USE_RGB_COLORS", Some("1")),
            ("DISPLAY_RESX", Some("240")),
            ("DISPLAY_RESY", Some("240")),
        ]);
    } else if cfg!(feature = "model_t2t1") {
        if cfg!(feature = "mcu_stm32f4") {
            lib.add_sources(&[
                "display/st-7789/display_nofb.c",
                "display/st-7789/display_driver.c",
                "display/st-7789/display_io.c",
                "display/st-7789/display_panel.c",
                "display/st-7789/panels/tf15411a.c",
                "display/st-7789/panels/154a.c",
                "display/st-7789/panels/lx154a2411.c",
                "display/st-7789/panels/lx154a2422.c",
            ]);
        } else if cfg!(feature = "mcu_emulator") {
            lib.add_source("display/unix/display_driver.c");
        } else {
            unimplemented!()
        }

        lib.add_public_defines(&[
            ("DISPLAY_RGB565", Some("1")),
            ("USE_RGB_COLORS", Some("1")),
            ("DISPLAY_RESX", Some("240")),
            ("DISPLAY_RESY", Some("240")),
        ]);
    } else if cfg!(feature = "model_t2b1") || cfg!(feature = "model_t3b1") {
        if cfg!(feature = "mcu_stm32u58") || cfg!(feature = "mcu_stm32f4") {
            lib.add_source("display/vg-2864/display_driver.c");
        } else if cfg!(feature = "mcu_emulator") {
            lib.add_source("display/unix/display_driver.c");
        } else {
            unimplemented!()
        }

        lib.add_public_defines(&[
            ("FRAMEBUFFER", Some("1")),
            ("DISPLAY_RESX", Some("128")),
            ("DISPLAY_RESY", Some("64")),
        ]);
    } else {
        unimplemented!();
    }

    if cfg!(feature = "mcu_emulator") {
        lib.add_source("display/unix/display_driver.c");
    }
}
