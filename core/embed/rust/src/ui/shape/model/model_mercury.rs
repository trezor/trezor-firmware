use crate::ui::{
    canvas::{BasicCanvas, Viewport},
    display::Color,
    geometry::{Offset, Rect},
    shape::{DrawingCache, ProgressiveRenderer},
};

use crate::trezorhal::bitmap::{BitmapView, Dma2d};

use static_alloc::Bump;

pub fn render_on_display<'a, F>(clip: Option<Rect>, bg_color: Option<Color>, func: F)
where
    F: FnOnce(&mut ProgressiveRenderer<'_, 'a, Bump<[u8; 40 * 1024]>, DisplayModelMercury>),
{
    #[link_section = ".no_dma_buffers"]
    static mut BUMP_A: Bump<[u8; 40 * 1024]> = Bump::uninit();

    #[link_section = ".buf"]
    static mut BUMP_B: Bump<[u8; 16 * 1024]> = Bump::uninit();

    let bump_a = unsafe { &mut *core::ptr::addr_of_mut!(BUMP_A) };
    let bump_b = unsafe { &mut *core::ptr::addr_of_mut!(BUMP_B) };
    {
        bump_a.reset();
        bump_b.reset();

        let cache = DrawingCache::new(bump_a, bump_b);
        let mut canvas = DisplayModelMercury::acquire().unwrap();

        if let Some(clip) = clip {
            canvas.set_viewport(Viewport::new(clip));
        }

        let mut target = ProgressiveRenderer::new(&mut canvas, bg_color, &cache, bump_a, 45);

        func(&mut target);

        target.render(16);
    }
}

pub struct DisplayModelMercury {
    size: Offset,
    viewport: Viewport,
}

impl DisplayModelMercury {
    pub fn acquire() -> Option<Self> {
        let size = Offset::new(240, 240); // TODO
        let viewport = Viewport::from_size(size);
        Some(Self { size, viewport })
    }
}

impl BasicCanvas for DisplayModelMercury {
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
        Dma2d::wnd565_fill(r, self.viewport.clip, color);
    }

    fn draw_bitmap(&mut self, r: Rect, bitmap: BitmapView) {
        let r = r.translate(self.viewport.origin);
        Dma2d::wnd565_copy(r, self.viewport.clip, &bitmap);
    }
}
