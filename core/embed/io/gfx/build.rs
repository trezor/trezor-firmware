// Defines io/gfx module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("gfx/inc");

    if cfg!(feature = "fancy_fatal_error") {
        lib.add_public_define("FANCY_FATAL_ERROR", Some("1"));
    }

    // !@# add dma2d feature

    if cfg!(feature = "mcu_stm32") {
        lib.add_source("gfx/bitblt/stm32/dma2d_bitblt.c");
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
}
