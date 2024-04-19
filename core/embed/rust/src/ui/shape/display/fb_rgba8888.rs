use crate::ui::{
    display::Color,
    geometry::Offset,
    shape::{BasicCanvas, DirectRenderer, DrawingCache, Rgba8888Canvas, Viewport},
};

use static_alloc::Bump;

use crate::trezorhal::display;

/// Creates the `Renderer` object for drawing on a display and invokes a
/// user-defined function that takes a single argument `target`. The user's
/// function can utilize the `target` for drawing on the display.
///
/// `clip` specifies a rectangle area that the user will draw to.
/// If no clip is specified, the entire display area is used.
///
/// `bg_color` specifies a background color with which the clip is filled before
/// the drawing starts. If the background color is None, the background
/// is undefined, and the user has to fill it themselves.
pub fn render_on_display<'a, F>(viewport: Option<Viewport>, bg_color: Option<Color>, func: F)
where
    F: FnOnce(&mut DirectRenderer<'_, 'a, Rgba8888Canvas<'a>>),
{
    const BUMP_A_SIZE: usize = DrawingCache::get_bump_a_size();
    const BUMP_B_SIZE: usize = DrawingCache::get_bump_b_size();

    #[cfg_attr(not(target_os = "macos"), link_section = ".no_dma_buffers")]
    static mut BUMP_A: Bump<[u8; BUMP_A_SIZE]> = Bump::uninit();

    #[cfg_attr(not(target_os = "macos"), link_section = ".buf")]
    static mut BUMP_B: Bump<[u8; BUMP_B_SIZE]> = Bump::uninit();

    let bump_a = unsafe { &mut *core::ptr::addr_of_mut!(BUMP_A) };
    let bump_b = unsafe { &mut *core::ptr::addr_of_mut!(BUMP_B) };
    {
        let width = display::DISPLAY_RESX as i16;
        let height = display::DISPLAY_RESY as i16;

        bump_a.reset();
        bump_b.reset();

        let cache = DrawingCache::new(bump_a, bump_b);

        let (fb, fb_stride) = display::get_frame_buffer();

        let mut canvas = unwrap!(Rgba8888Canvas::new(
            Offset::new(width, height),
            Some(fb_stride),
            None,
            fb
        ));

        if let Some(viewport) = viewport {
            canvas.set_viewport(Viewport::new(viewport));
        }

        let mut target = DirectRenderer::new(&mut canvas, bg_color, &cache);

        func(&mut target);
    }
}
