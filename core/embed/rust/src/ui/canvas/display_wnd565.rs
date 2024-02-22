use crate::ui::{
    display::Color,
    geometry::{Offset, Rect},
};

use super::{BasicCanvas, BitmapView, Viewport};

use crate::trezorhal::bitmap::Dma2d;

// ==========================================================================
// Display canvas
// ==========================================================================

pub struct Wnd565Display {
    size: Offset,
    viewport: Viewport,
}

impl Wnd565Display {
    pub fn acquire() -> Option<Self> {
        let size = Offset::new(240, 240); // TODO
        let viewport = Viewport::from_size(size);
        Some(Self { size, viewport })
    }
}

impl BasicCanvas for Wnd565Display {
    fn viewport(&self) -> Viewport {
        self.viewport
    }

    fn set_viewport(&mut self, viewport: Viewport) {
        self.viewport = viewport.absolute_clip(self.bounds());
    }

    fn size(&self) -> Offset {
        self.size
    }

    fn fill_rect(&mut self, r: Rect, color: Color) {
        let r = r.translate(self.viewport.origin);
        Dma2d::wnd565_fill(r, self.viewport.clip, color);
    }

    fn draw_bitmap(&mut self, r: Rect, bitmap: BitmapView) {
        let r = r.translate(self.viewport.origin);
        Dma2d::wnd565_copy(r, self.viewport.clip, &bitmap);
    }
}
