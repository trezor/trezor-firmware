use crate::ui::{
    display::Color,
    geometry::{Offset, Rect},
    shape::{BasicCanvas, DirectRenderer, DrawingCache, Mono8Canvas, Viewport},
};

use crate::trezorhal::display;

use static_alloc::Bump;

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
pub fn render_on_display<'a, F>(clip: Option<Rect>, bg_color: Option<Color>, func: F)
where
    F: FnOnce(&mut DirectRenderer<'_, 'a, Mono8Canvas<'a>>),
{
    const BUMP_SIZE: usize = DrawingCache::get_bump_a_size() + DrawingCache::get_bump_b_size();

    static mut BUMP: Bump<[u8; BUMP_SIZE]> = Bump::uninit();

    let bump = unsafe { &mut *core::ptr::addr_of_mut!(BUMP) };
    {
        let width = display::DISPLAY_RESX as i16;
        let height = display::DISPLAY_RESY as i16;

        bump.reset();

        let cache = DrawingCache::new(bump, bump);

        let (fb, fb_stride) = display::get_frame_buffer();

        let mut canvas = unwrap!(Mono8Canvas::new(
            Offset::new(width, height),
            Some(fb_stride),
            None,
            fb
        ));

        if let Some(clip) = clip {
            canvas.set_viewport(Viewport::new(clip));
        }

        let mut target = DirectRenderer::new(&mut canvas, bg_color, &cache);

        func(&mut target);
    }
}
