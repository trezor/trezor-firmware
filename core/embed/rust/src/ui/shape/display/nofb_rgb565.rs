use crate::trezorhal::{bitblt::BitBlt, display};

use crate::ui::{
    display::Color,
    geometry::{Offset, Rect},
};

use super::super::{
    BasicCanvas, BitmapFormat, BitmapView, DrawingCache, ProgressiveRenderer, Viewport,
};

use static_alloc::Bump;

// Maximum number of shapes on a single screen
const SHAPE_MAX_COUNT: usize = 45;
// Memory reserved for ProgressiveRenderes shape storage
const SHAPE_MEM_SIZE: usize = 5 * 1024;
// Memory not accessible by DMA
const BUMP_A_SIZE: usize = DrawingCache::get_bump_a_size() + SHAPE_MEM_SIZE;
// Memory accessible by DMA
const BUMP_B_SIZE: usize = DrawingCache::get_bump_b_size();

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
    F: FnOnce(&mut ProgressiveRenderer<'_, 'a, Bump<[u8; BUMP_A_SIZE]>, DisplayCanvas>),
{
    #[cfg_attr(not(target_os = "macos"), link_section = ".no_dma_buffers")]
    static mut BUMP_A: Bump<[u8; BUMP_A_SIZE]> = Bump::uninit();

    #[cfg_attr(not(target_os = "macos"), link_section = ".buf")]
    static mut BUMP_B: Bump<[u8; BUMP_B_SIZE]> = Bump::uninit();

    let bump_a = unsafe { &mut *core::ptr::addr_of_mut!(BUMP_A) };
    let bump_b = unsafe { &mut *core::ptr::addr_of_mut!(BUMP_B) };
    {
        bump_a.reset();
        bump_b.reset();

        let cache = DrawingCache::new(bump_a, bump_b);
        let mut canvas = DisplayCanvas::new();

        if let Some(clip) = clip {
            canvas.set_viewport(Viewport::new(clip));
        }

        let mut target =
            ProgressiveRenderer::new(&mut canvas, bg_color, &cache, bump_a, SHAPE_MAX_COUNT);

        func(&mut target);

        target.render(16);
    }
}

/// A simple display canvas allowing just two bitblt operations:
/// 'fill_rect' and 'draw_bitmap` needed by `ProgressiveRenderer`.
pub struct DisplayCanvas {
    size: Offset,
    viewport: Viewport,
}

impl DisplayCanvas {
    pub fn new() -> Self {
        let size = Offset::new(display::DISPLAY_RESX as i16, display::DISPLAY_RESY as i16);
        let viewport = Viewport::from_size(size);
        Self { size, viewport }
    }
}

impl BasicCanvas for DisplayCanvas {
    fn viewport(&self) -> Viewport {
        self.viewport
    }

    fn set_viewport(&mut self, viewport: Viewport) {
        self.viewport = viewport.absolute_clip(self.bounds());
    }

    fn size(&self) -> Offset {
        self.size
    }

    fn fill_rect(&mut self, r: Rect, color: Color, _alpha: u8) {
        let r = r.translate(self.viewport.origin);
        if let Some(bitblt) = BitBlt::new_fill(r, self.viewport.clip, color, 255) {
            unsafe { bitblt.display_fill() };
        }
    }

    fn draw_bitmap(&mut self, r: Rect, bitmap: BitmapView) {
        let r = r.translate(self.viewport.origin);
        if let Some(bitblt) = BitBlt::new_copy(r, self.viewport.clip, &bitmap) {
            match bitmap.format() {
                BitmapFormat::RGB565 => unsafe { bitblt.display_copy_rgb565() },
                _ => panic!("Unsupported DMA operation"),
            }
            bitmap.bitmap.mark_dma_pending();
        }
    }
}
