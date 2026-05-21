use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("gfx/inc");

    if cfg!(feature = "fancy_fatal_error") {
        lib.add_define("FANCY_FATAL_ERROR", Some("1"));
    }

    lib.add_source("gfx/bitblt/gfx_bitblt_mono8.c");
    lib.add_source("gfx/bitblt/gfx_bitblt_rgb565.c");
    lib.add_source("gfx/bitblt/gfx_bitblt_rgba8888.c");
    lib.add_source("gfx/bitblt/gfx_bitblt.c");

    lib.add_source("gfx/terminal/terminal.c");
    lib.add_source("gfx/terminal/font_bitmap.c");

    lib.add_source("gfx/gfx_draw.c");
    lib.add_source("gfx/gfx_color.c");
    lib.add_source("gfx/rsod.c");

    if cfg!(feature = "emulator") {
        // No DMA2D implementation
    } else if cfg!(feature = "mcu_stm32") {
        if cfg!(feature = "dma2d") {
            lib.add_define("USE_DMA2D", Some("1"));
            lib.add_source("gfx/bitblt/stm32/dma2d_bitblt.c");
        }
    } else {
        bail_unsupported!();
    }

    if cfg!(feature = "hw_jpeg_decoder") {
        lib.add_define("USE_HW_JPEG_DECODER", Some("1"));

        if cfg!(feature = "emulator") {
            lib.add_source("gfx/jpegdec/unix/jpegdec.c");

            lib.import_external_lib("libjpeg", false)?;
        } else if cfg!(feature = "mcu_stm32u5g") {
            lib.add_source("gfx/jpegdec/stm32u5/jpegdec.c");
        } else {
            bail_unsupported!();
        }
    }

    Ok(())
}
