use crate::ui::{
    display::Color,
    geometry::{Offset, Rect},
    shape::{BasicCanvas, DirectRenderer, DrawingCache, Rgba8888Canvas, Viewport},
};

use static_alloc::Bump;

use crate::trezorhal::display;

pub fn render_on_display<'a, F>(clip: Option<Rect>, bg_color: Option<Color>, func: F)
where
    F: FnOnce(&mut DirectRenderer<'_, 'a, Rgba8888Canvas<'a>>),
{
    #[link_section = ".no_dma_buffers"]
    static mut BUMP_A: Bump<[u8; 40 * 1024]> = Bump::uninit();

    #[link_section = ".buf"]
    static mut BUMP_B: Bump<[u8; 16 * 1024]> = Bump::uninit();

    let bump_a = unsafe { &mut *core::ptr::addr_of_mut!(BUMP_A) };
    let bump_b = unsafe { &mut *core::ptr::addr_of_mut!(BUMP_B) };
    {
        let width = display::DISPLAY_RESX as i16;
        let height = display::DISPLAY_RESY as i16;

        bump_a.reset();
        bump_b.reset();

        let cache = DrawingCache::new(bump_a, bump_b);

        let fb = unsafe {
            core::slice::from_raw_parts_mut(
                display::get_frame_addr() as *mut u8,
                width as usize * height as usize * core::mem::size_of::<u32>(),
            )
        };

        let mut canvas = unwrap!(Rgba8888Canvas::new(Offset::new(width, height), None, fb));

        if let Some(clip) = clip {
            canvas.set_viewport(Viewport::new(clip));
        }

        let mut target = DirectRenderer::new(&mut canvas, bg_color, &cache);

        func(&mut target);

        display::refresh();
    }
}
