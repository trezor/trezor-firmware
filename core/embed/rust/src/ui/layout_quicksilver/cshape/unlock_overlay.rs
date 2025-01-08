use crate::ui::{
    display::Color,
    geometry::{Offset, Point, Rect},
    shape::{Canvas, DrawingCache, Mono8Canvas, Renderer, Shape, ShapeClone},
};

use without_alloc::alloc::LocalAllocLeakExt;

/// A special shape for rendering 7 differently rotated circular
/// sectors on 5 concentric circles, used as an overlay on the background
/// image on the lock screen.
///
/// The overlay covers area of 170x170 pixels (centered at `pos`).
pub struct UnlockOverlay {
    /// Center of the overlay
    pos: Point,
    // Angle of the rotation (in degrees)
    angle: f32,
}

impl UnlockOverlay {
    /// Outer radius
    pub const RADIUS: i16 = 85;
    /// Distance between the circles
    pub const SPAN: i16 = 10;
    /// Thickness of the circles
    pub const THICKNESS: i16 = 4;

    /// Create a new overlay with the given center and rotation angle.
    pub fn new(pos: Point, angle: f32) -> Self {
        Self { pos, angle }
    }

    pub fn render<'a>(self, renderer: &mut impl Renderer<'a>) {
        renderer.render_shape(self);
    }

    fn prepare_overlay(&self, canvas: &mut dyn Canvas) {
        let center = canvas.bounds().center();

        let transp = Color::black();
        let opaque = Color::white();

        canvas.fill_background(opaque);

        // The most outer circle (with two sectors)
        let angle = self.angle;
        let r = Self::RADIUS;
        canvas.fill_sector(center, r, 0.0 + angle, 140.0 + angle, transp);
        canvas.fill_sector(center, r, 235.0 + angle, 270.0 + angle, transp);
        canvas.fill_circle(center, r - Self::THICKNESS, opaque, 255);

        // The second circle (with one sector)
        let angle = -self.angle - 20.0;
        let r = Self::RADIUS - Self::SPAN;
        canvas.fill_sector(center, r, 0.0 + angle, 135.0 + angle, transp);
        canvas.fill_circle(center, r - Self::THICKNESS, opaque, 255);

        // The third circle (with one sector)
        let angle = self.angle / 2.0 + 90.0;
        let r = Self::RADIUS - 2 * Self::SPAN;
        canvas.fill_sector(center, r, 0.0 + angle, 270.0 + angle, transp);
        canvas.fill_circle(center, r - Self::THICKNESS, opaque, 255);

        // The fourth circle (with two sectors)
        let angle = -self.angle / 2.0 + 60.0;
        let r = Self::RADIUS - 3 * Self::SPAN;
        canvas.fill_sector(center, r, 0.0 + angle, 110.0 + angle, transp);
        canvas.fill_sector(center, r, 180.0 + angle, 280.0 + angle, transp);
        canvas.fill_circle(center, r - Self::THICKNESS, opaque, 255);

        // Inner fixed circle
        let r = Self::RADIUS - (9 * Self::SPAN) / 2 - 1;
        canvas.fill_circle(center, r, transp, 255);
        canvas.fill_circle(center, r - Self::THICKNESS, opaque, 255);
    }
}

impl<'a> Shape<'a> for UnlockOverlay {
    fn bounds(&self) -> Rect {
        // +1 pixel because middle pixel is not counted in circle radius
        Rect::new(
            self.pos - Offset::uniform(Self::RADIUS + 1),
            self.pos + Offset::uniform(Self::RADIUS + 2),
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

        self.prepare_overlay(&mut overlay_canvas);

        canvas.blend_bitmap(bounds, overlay_canvas.view().with_fg(Color::black()));
    }
}

impl<'a> ShapeClone<'a> for UnlockOverlay {
    fn clone_at_bump<T>(self, bump: &'a T) -> Option<&'a mut dyn Shape<'a>>
    where
        T: LocalAllocLeakExt<'a>,
    {
        let clone = bump.alloc_t()?;
        Some(clone.uninit.init(UnlockOverlay { ..self }))
    }
}
