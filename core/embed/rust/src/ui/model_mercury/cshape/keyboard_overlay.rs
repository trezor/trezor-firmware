use crate::ui::{
    display::Color,
    geometry::Rect,
    shape::{Canvas, DrawingCache, Mono8Canvas, Renderer, Shape, ShapeClone},
};

use without_alloc::alloc::LocalAllocLeakExt;

/// A special shape for rendering keyboard overlay.
/// Makes the corner buttons have rounded corners.
pub struct KeyboardOverlay {
    /// Center of the overlay
    area: Rect,
}

impl KeyboardOverlay {
    pub const RADIUS: i16 = 6;

    /// Create a new overlay with given area
    pub fn new(area: Rect) -> Self {
        Self { area }
    }

    pub fn render<'a>(self, renderer: &mut impl Renderer<'a>) {
        renderer.render_shape(self);
    }

    fn prepare_overlay(&self, canvas: &mut dyn Canvas) {
        let area = canvas.bounds();

        let transp = Color::black();
        let opaque = Color::white();

        canvas.fill_background(opaque);

        canvas.fill_round_rect(area, 6, transp, 0xFF);
    }
}

impl<'a> Shape<'a> for KeyboardOverlay {
    fn bounds(&self) -> Rect {
        self.area
    }

    fn draw(&mut self, canvas: &mut dyn Canvas, cache: &DrawingCache<'a>) {
        let bounds = self.bounds();

        let overlay_buff = &mut unwrap!(cache.image_buff(), "No image buffer");

        let mut overlay_canvas = unwrap!(
            Mono8Canvas::new(bounds.size(), None, None, &mut overlay_buff[..]),
            "Too small buffer"
        );

        self.prepare_overlay(&mut overlay_canvas);

        canvas.blend_bitmap(bounds, overlay_canvas.view().with_fg(Color::black()));
    }

    fn cleanup(&mut self, _cache: &DrawingCache<'a>) {}
}

impl<'a> ShapeClone<'a> for KeyboardOverlay {
    fn clone_at_bump<T>(self, bump: &'a T) -> Option<&'a mut dyn Shape<'a>>
    where
        T: LocalAllocLeakExt<'a>,
    {
        let clone = bump.alloc_t()?;
        Some(clone.uninit.init(KeyboardOverlay { ..self }))
    }
}
