use crate::ui::{
    display::Color,
    geometry::{Offset, Point, Rect},
};

use super::{Canvas, DrawingCache, Mono8Canvas, Renderer, Shape, ShapeClone};

use without_alloc::alloc::LocalAllocLeakExt;

/// A shape for rendering compressed TOIF images.
pub struct FancyOverlay {
    /// Image position
    pos: Point,
    radius: i16,
    offset: f32,
}

impl FancyOverlay {
    pub fn new(pos: Point, offset: f32) -> Self {
        Self {
            pos,
            radius: 85,
            offset,
        }
    }

    pub fn render<'a>(self, renderer: &mut impl Renderer<'a>) {
        renderer.render_shape(self);
    }

    fn draw_overlay(&self, canvas: &mut dyn Canvas) {
        let center = canvas.bounds().center();

        let visible = Color::black();
        let hidden = Color::white();

        canvas.fill_background(hidden);

        let th = 4;

        let ofs = self.offset;
        let r = self.radius;
        canvas.fill_sector(center, r, 0.0 + ofs, 140.0 + ofs, visible);
        canvas.fill_sector(center, r, 235.0 + ofs, 270.0 + ofs, visible);
        canvas.fill_circle(center, r - th, hidden);

        let ofs = -self.offset - 20.0;
        let r = self.radius - 10;
        canvas.fill_sector(center, r, 0.0 + ofs, 135.0 + ofs, visible);
        canvas.fill_circle(center, r - th, hidden);

        let ofs = self.offset / 2.0 + 90.0;
        let r = self.radius - 20;
        canvas.fill_sector(center, r, 0.0 + ofs, 270.0 + ofs, visible);
        canvas.fill_circle(center, r - th, hidden);

        let ofs = -self.offset / 2.0 + 60.0;
        let r = self.radius - 30;
        canvas.fill_sector(center, r, 0.0 + ofs, 110.0 + ofs, visible);
        canvas.fill_sector(center, r, 180.0 + ofs, 280.0 + ofs, visible);
        canvas.fill_circle(center, r - th, hidden);

        let r = self.radius - 45;
        canvas.fill_circle(center, r, visible);
        canvas.fill_circle(center, r - th, hidden);
    }
}

impl<'a> Shape<'a> for FancyOverlay {
    fn bounds(&self) -> Rect {
        Rect::new(
            self.pos - Offset::uniform(self.radius),
            self.pos + Offset::uniform(self.radius + 1),
        )
    }

    fn cleanup(&mut self, _cache: &DrawingCache<'a>) {
        // TODO: inform the cache that we won't use the zlib slot anymore
    }

    fn draw(&mut self, canvas: &mut dyn Canvas, cache: &DrawingCache<'a>) {
        let bounds = self.bounds();

        let overlay_buff = &mut unwrap!(cache.image_buff(), "No image buffer");

        let mut overlay_canvas = unwrap!(
            Mono8Canvas::new(bounds.size(), None, None, &mut overlay_buff[..]),
            "Too small buffer"
        );

        self.draw_overlay(&mut overlay_canvas);

        canvas.blend_bitmap(bounds, overlay_canvas.view().with_fg(Color::black()));
    }
}

impl<'a> ShapeClone<'a> for FancyOverlay {
    fn clone_at_bump<T>(self, bump: &'a T) -> Option<&'a mut dyn Shape<'a>>
    where
        T: LocalAllocLeakExt<'a>,
    {
        let clone = bump.alloc_t()?;
        Some(clone.uninit.init(FancyOverlay { ..self }))
    }
}
