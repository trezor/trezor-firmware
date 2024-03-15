use crate::ui::{
    display::Color,
    geometry::{Offset, Point, Rect},
};

use super::super::{
    algo::{circle_points, line_points, sin_i16, PI4},
    BitmapView, Viewport,
};

#[cfg(feature = "ui_blurring")]
use crate::ui::shape::DrawingCache;

pub trait BasicCanvas {
    /// Returns dimensions of the canvas in pixels.
    fn size(&self) -> Offset;

    /// Returns the dimensions of the canvas as a rectangle with
    /// the top-left at (0,0).
    fn bounds(&self) -> Rect {
        Rect::from_size(self.size())
    }

    /// Returns the width of the canvas in pixels.
    fn width(&self) -> i16 {
        self.size().x
    }

    /// Returns the height of the canvas in pixels.
    fn height(&self) -> i16 {
        self.size().y
    }

    /// Gets the current drawing viewport previously set by `set_viewport()`
    /// function.
    fn viewport(&self) -> Viewport;

    /// Sets the active viewport valid for all subsequent drawing operations.
    fn set_viewport(&mut self, vp: Viewport);

    /// Sets the new viewport that's intersection of the
    /// current viewport and the `window` rectangle relative
    /// to the current viewport. The viewport's origin is
    /// set to the top-left corener of the `window`.
    fn set_window(&mut self, window: Rect) -> Viewport {
        let viewport = self.viewport();
        self.set_viewport(viewport.relative_window(window));
        viewport
    }

    /// Sets the new viewport that's intersection of the
    /// current viewport and the `clip` rectangle relative
    /// to the current viewport. The viewport's origin is
    /// not changed.
    fn set_clip(&mut self, clip: Rect) -> Viewport {
        let viewport = self.viewport();
        self.set_viewport(viewport.relative_clip(clip));
        viewport
    }

    /// Draws a filled rectangle with the specified color.
    fn fill_rect(&mut self, r: Rect, color: Color, alpha: u8);

    /// Fills the canvas background with the specified color.
    fn fill_background(&mut self, color: Color) {
        self.fill_rect(self.viewport().clip, color, 255);
    }

    /// Draws a bitmap of bitmap into to the rectangle.
    fn draw_bitmap(&mut self, r: Rect, bitmap: BitmapView);
}

pub trait Canvas: BasicCanvas {
    /// Returns a non-mutable view of the underlying bitmap.
    fn view(&self) -> BitmapView;

    /// Draw a pixel at specified coordinates.
    fn draw_pixel(&mut self, pt: Point, color: Color);

    /// Draws a single pixel and blends its color with the background.
    ///
    /// - If alpha == 255, the (foreground) pixel color is used.
    /// - If 0 < alpha << 255, pixel and backround colors are blended.
    /// - If alpha == 0, the background color is used.
    fn blend_pixel(&mut self, pt: Point, color: Color, alpha: u8);

    /// Blends a bitmap with the canvas background
    fn blend_bitmap(&mut self, r: Rect, src: BitmapView);

    /// Applies a blur effect to the specified rectangle.
    ///
    /// The blur effect works properly only when the rectangle is not clipped,
    /// which is a strong constraint that's hard to be met. The function uses a
    /// simple box filter, where the 'radius' argument represents the length
    /// of the sides of this filter.
    ///
    /// It's important to be aware that strong artifacts may appear on images
    /// with horizontal/vertical lines.
    #[cfg(feature = "ui_blurring")]
    fn blur_rect(&mut self, r: Rect, radius: usize, cache: &DrawingCache);

    /// Draws an outline of a rectangle with rounded corners.
    fn draw_round_rect(&mut self, r: Rect, radius: i16, color: Color) {
        let split = unwrap!(circle_points(radius).last()).v;

        let b = Rect {
            y1: r.y0 + radius - split + 1,
            ..r
        };

        if self.viewport().contains(b) {
            for p in circle_points(radius) {
                let pt_l = Point::new(r.x0 + radius - p.u, r.y0 + radius - p.v);
                let pt_r = Point::new(r.x1 - radius + p.u - 1, r.y0 + radius - p.v);
                if p.v == radius && p.last {
                    self.fill_rect(Rect::new(pt_l, pt_r.onright().under()), color, 255);
                } else {
                    self.draw_pixel(pt_l, color);
                    self.draw_pixel(pt_r, color);
                }
            }
        }

        let b = Rect {
            y0: r.y0 + radius - split + 1,
            y1: r.y0 + radius + 1,
            ..r
        };

        if self.viewport().contains(b) {
            for p in circle_points(radius).take_while(|p| p.u < p.v) {
                let pt_l = Point::new(r.x0 + radius - p.v, r.y0 + radius - p.u);
                let pt_r = Point::new(r.x1 - radius + p.v - 1, r.y0 + radius - p.u);
                self.draw_pixel(pt_l, color);
                self.draw_pixel(pt_r, color);
            }
        }

        self.fill_rect(
            Rect {
                x0: r.x0,
                y0: r.y0 + radius + 1,
                x1: r.x0 + 1,
                y1: r.y1 - radius - 1,
            },
            color,
            255,
        );

        self.fill_rect(
            Rect {
                x0: r.x1 - 1,
                y0: r.y0 + radius + 1,
                x1: r.x1,
                y1: r.y1 - radius - 1,
            },
            color,
            255,
        );

        let b = Rect {
            y0: r.y1 - radius - 1,
            y1: r.y1 - radius - 1 + split,
            ..r
        };

        if self.viewport().contains(b) {
            for p in circle_points(radius).take_while(|p| p.u < p.v) {
                let pt_l = Point::new(r.x0 + radius - p.v, r.y1 - radius - 1 + p.u);
                let pt_r = Point::new(r.x1 - radius + p.v - 1, r.y1 - radius - 1 + p.u);
                self.draw_pixel(pt_l, color);
                self.draw_pixel(pt_r, color);
            }
        }

        let b = Rect {
            y0: r.y1 - radius - 1 + split,
            ..r
        };

        if self.viewport().contains(b) {
            for p in circle_points(radius) {
                let pt_l = Point::new(r.x0 + radius - p.u, r.y1 - radius - 1 + p.v);
                let pt_r = Point::new(r.x1 - radius + p.u - 1, r.y1 - radius - 1 + p.v);

                if p.v == radius && p.last {
                    self.fill_rect(Rect::new(pt_l, pt_r.onright().under()), color, 255);
                } else {
                    self.draw_pixel(pt_l, color);
                    self.draw_pixel(pt_r, color);
                }
            }
        }
    }

    /// Draws filled rectangle with rounded corners.
    #[cfg(not(feature = "ui_antialiasing"))]
    fn fill_round_rect(&mut self, r: Rect, radius: i16, color: Color, alpha: u8) {
        let split = unwrap!(circle_points(radius).last()).v;

        let b = Rect {
            y1: r.y0 + radius - split + 1,
            ..r
        };

        if self.viewport().contains(b) {
            for p in circle_points(radius) {
                if p.last {
                    let pt_l = Point::new(r.x0 + radius - p.u, r.y0 + radius - p.v);
                    let pt_r = Point::new(r.x1 - radius + p.u - 1, r.y0 + radius - p.v);
                    self.fill_rect(Rect::new(pt_l, pt_r.onright().under()), color, alpha);
                }
            }
        }

        let b = Rect {
            y0: r.y0 + radius - split + 1,
            y1: r.y0 + radius + 1,
            ..r
        };

        if self.viewport().contains(b) {
            for p in circle_points(radius).take_while(|p| p.u < p.v) {
                let pt_l = Point::new(r.x0 + radius - p.v, r.y0 + radius - p.u);
                let pt_r = Point::new(r.x1 - radius + p.v - 1, r.y0 + radius - p.u);
                self.fill_rect(Rect::new(pt_l, pt_r.onright().under()), color, alpha);
            }
        }

        self.fill_rect(
            Rect {
                x0: r.x0,
                y0: r.y0 + radius + 1,
                x1: r.x1,
                y1: r.y1 - radius - 1,
            },
            color,
            alpha,
        );

        let b = Rect {
            y0: r.y1 - radius - 1,
            y1: r.y1 - radius - 1 + split,
            ..r
        };

        if self.viewport().contains(b) {
            for p in circle_points(radius).take_while(|p| p.u < p.v) {
                let pt_l = Point::new(r.x0 + radius - p.v, r.y1 - radius - 1 + p.u);
                let pt_r = Point::new(r.x1 - radius + p.v - 1, r.y1 - radius - 1 + p.u);
                self.fill_rect(Rect::new(pt_l, pt_r.onright().under()), color, alpha);
            }
        }

        let b = Rect {
            y0: r.y1 - radius - 1 + split,
            ..r
        };

        if self.viewport().contains(b) {
            for p in circle_points(radius) {
                if p.last {
                    let pt_l = Point::new(r.x0 + radius - p.u, r.y1 - radius - 1 + p.v);
                    let pt_r = Point::new(r.x1 - radius + p.u - 1, r.y1 - radius - 1 + p.v);
                    self.fill_rect(Rect::new(pt_l, pt_r.onright().under()), color, alpha);
                }
            }
        }
    }

    /// Draws filled rectangle with antialiased rounded corners.
    #[cfg(feature = "ui_antialiasing")]
    fn fill_round_rect(&mut self, r: Rect, radius: i16, color: Color, alpha: u8) {
        let split = unwrap!(circle_points(radius).last()).v;

        let b = Rect {
            y1: r.y0 + radius - split + 1,
            ..r
        };

        let alpha_mul = |a: u8| -> u8 { ((a as u16 * alpha as u16) / 255) as u8 };

        if self.viewport().contains(b) {
            for p in circle_points(radius) {
                let pt_l = Point::new(r.x0 + radius - p.u, r.y0 + radius - p.v);
                let pt_r = Point::new(r.x1 - radius + p.u - 1, r.y0 + radius - p.v);
                self.blend_pixel(pt_l, color, alpha_mul(p.frac));
                self.blend_pixel(pt_r, color, alpha_mul(p.frac));

                if p.first {
                    let inner = Rect::new(pt_l.onright(), pt_r.under());
                    self.fill_rect(inner, color, alpha);
                }
            }
        }

        let b = Rect {
            y0: r.y0 + radius - split + 1,
            y1: r.y0 + radius + 1,
            ..r
        };

        if self.viewport().contains(b) {
            for p in circle_points(radius).take_while(|p| p.u < p.v) {
                let pt_l = Point::new(r.x0 + radius - p.v, r.y0 + radius - p.u);
                let pt_r = Point::new(r.x1 - radius + p.v - 1, r.y0 + radius - p.u);
                self.blend_pixel(pt_l, color, alpha_mul(p.frac));
                self.blend_pixel(pt_r, color, alpha_mul(p.frac));

                let inner = Rect::new(pt_l.onright(), pt_r.under());
                self.fill_rect(inner, color, alpha);
            }
        }

        self.fill_rect(
            Rect {
                x0: r.x0,
                y0: r.y0 + radius + 1,
                x1: r.x1,
                y1: r.y1 - radius - 1,
            },
            color,
            alpha,
        );

        let b = Rect {
            y0: r.y1 - radius - 1,
            y1: r.y1 - radius - 1 + split,
            ..r
        };

        if self.viewport().contains(b) {
            for p in circle_points(radius).take_while(|p| p.u < p.v) {
                let pt_l = Point::new(r.x0 + radius - p.v, r.y1 - radius - 1 + p.u);
                let pt_r = Point::new(r.x1 - radius + p.v - 1, r.y1 - radius - 1 + p.u);
                self.blend_pixel(pt_l, color, alpha_mul(p.frac));
                self.blend_pixel(pt_r, color, alpha_mul(p.frac));

                let b = Rect::new(pt_l.onright(), pt_r.under());
                self.fill_rect(b, color, alpha);
            }
        }

        let b = Rect {
            y0: r.y1 - radius - 1 + split,
            ..r
        };

        if self.viewport().contains(b) {
            for p in circle_points(radius) {
                let pt_l = Point::new(r.x0 + radius - p.u, r.y1 - radius - 1 + p.v);
                self.blend_pixel(pt_l, color, alpha_mul(p.frac));
                let pt_r = Point::new(r.x1 - radius + p.u - 1, r.y1 - radius - 1 + p.v);
                self.blend_pixel(pt_r, color, alpha_mul(p.frac));

                if p.first {
                    let b = Rect::new(pt_l.onright(), pt_r.under());
                    self.fill_rect(b, color, alpha);
                }
            }
        }
    }

    // Draws circle with the specified center and the radius.
    #[cfg(not(feature = "ui_antialiasing"))]
    fn draw_circle(&mut self, center: Point, radius: i16, color: Color) {
        let split = unwrap!(circle_points(radius).last()).v;

        let r = Rect::new(
            Point::new(center.x - radius, center.y - radius),
            Point::new(center.x + radius + 1, center.y - split + 1),
        );

        if self.viewport().contains(r) {
            for p in circle_points(radius) {
                let pt_l = Point::new(center.x - p.u, center.y - p.v);
                let pt_r = Point::new(center.x + p.u, center.y - p.v);
                self.draw_pixel(pt_l, color);
                self.draw_pixel(pt_r, color);
            }
        }

        let r = Rect::new(
            Point::new(center.x - radius, center.y - split),
            Point::new(center.x + radius + 1, center.y + 1),
        );

        if self.viewport().contains(r) {
            for p in circle_points(radius).take_while(|p| p.u < p.v) {
                let pt_l = Point::new(center.x - p.v, center.y - p.u);
                let pt_r = Point::new(center.x + p.v, center.y - p.u);
                self.draw_pixel(pt_l, color);
                self.draw_pixel(pt_r, color);
            }
        }

        let r = Rect::new(
            Point::new(center.x - radius, center.y + 1),
            Point::new(center.x + radius + 1, center.y + split + 1),
        );

        if self.viewport().contains(r) {
            for p in circle_points(radius).skip(1).take_while(|p| p.u < p.v) {
                let pt_l = Point::new(center.x - p.v, center.y + p.u);
                let pt_r = Point::new(center.x + p.v, center.y + p.u);
                self.draw_pixel(pt_l, color);
                self.draw_pixel(pt_r, color);
            }
        }

        let r = Rect::new(
            Point::new(center.x - radius, center.y + split),
            Point::new(center.x + radius + 1, center.y + radius + 1),
        );

        if self.viewport().contains(r) {
            for p in circle_points(radius) {
                let pt_l = Point::new(center.x - p.u, center.y + p.v);
                let pt_r = Point::new(center.x + p.u, center.y + p.v);
                self.draw_pixel(pt_l, color);
                self.draw_pixel(pt_r, color);
            }
        }
    }

    /// Draws antialiased circle with the specified center and the radius.
    /*#[cfg(feature = "ui_antialiasing")]
    fn draw_circle(&mut self, center: Point, radius: i16, color: Color) {
        let split = unwrap!(circle_points(radius).last()).v;

        let r = Rect::new(
            Point::new(center.x - radius, center.y - radius),
            Point::new(center.x + radius + 1, center.y - split + 1),
        );

        if self.viewport().contains(r) {
            for p in circle_points(radius) {
                let pt_l = Point::new(center.x - p.u, center.y - p.v);
                self.blend_pixel(pt_l, color, p.frac);
                self.blend_pixel(pt_l.under(), color, 255 - p.frac);
                let pt_r = Point::new(center.x + p.u, center.y - p.v);
                self.blend_pixel(pt_r, color, p.frac);
                self.blend_pixel(pt_r.under(), color, 255 - p.frac);
            }
        }

        let r = Rect::new(
            Point::new(center.x - radius, center.y - split),
            Point::new(center.x + radius + 1, center.y + 1),
        );

        if self.viewport().contains(r) {
            for p in circle_points(radius).take_while(|p| p.u < p.v) {
                let pt_l = Point::new(center.x - p.v, center.y - p.u);
                self.blend_pixel(pt_l, color, p.frac);
                self.blend_pixel(pt_l.onright(), color, 255 - p.frac);
                let pt_r = Point::new(center.x + p.v, center.y - p.u);
                self.blend_pixel(pt_r, color, p.frac);
                self.blend_pixel(pt_r.onleft(), color, 255 - p.frac);
            }
        }

        let r = Rect::new(
            Point::new(center.x - radius, center.y + 1),
            Point::new(center.x + radius + 1, center.y + split + 1),
        );

        if self.viewport().contains(r) {
            for p in circle_points(radius).skip(1).take_while(|p| p.u < p.v) {
                let pt_l = Point::new(center.x - p.v, center.y + p.u);
                self.blend_pixel(pt_l, color, p.frac);
                self.blend_pixel(pt_l.onright(), color, 255 - p.frac);
                let pt_r = Point::new(center.x + p.v, center.y + p.u);
                self.blend_pixel(pt_r, color, p.frac);
                self.blend_pixel(pt_r.onleft(), color, 255 - p.frac);
            }
        }

        let r = Rect::new(
            Point::new(center.x - radius, center.y + split),
            Point::new(center.x + radius + 1, center.y + radius + 1),
        );

        if self.viewport().contains(r) {
            for p in circle_points(radius) {
                let pt_l = Point::new(center.x - p.u, center.y + p.v);
                self.blend_pixel(pt_l, color, p.frac);
                self.blend_pixel(pt_l.above(), color, 255 - p.frac);
                let pt_r = Point::new(center.x + p.u, center.y + p.v);
                self.blend_pixel(pt_r, color, p.frac);
                self.blend_pixel(pt_r.above(), color, 255 - p.frac);
            }
        }
    }*/

    /// Draws filled circle with the specified center and the radius.
    #[cfg(not(feature = "ui_antialiasing"))]
    fn fill_circle(&mut self, center: Point, radius: i16, color: Color) {
        let split = unwrap!(circle_points(radius).last()).v;
        let alpha = 255;

        let r = Rect::new(
            Point::new(center.x - radius, center.y - radius),
            Point::new(center.x + radius + 1, center.y - split + 1),
        );

        if self.viewport().contains(r) {
            for p in circle_points(radius) {
                if p.last {
                    let pt_l = Point::new(center.x - p.u, center.y - p.v);
                    let pt_r = Point::new(center.x + p.u, center.y - p.v);
                    self.fill_rect(Rect::new(pt_l, pt_r.onright().under()), color, alpha);
                }
            }
        }

        let r = Rect::new(
            Point::new(center.x - radius, center.y - split),
            Point::new(center.x + radius + 1, center.y + 1),
        );

        if self.viewport().contains(r) {
            for p in circle_points(radius).take_while(|p| p.u < p.v) {
                let pt_l = Point::new(center.x - p.v, center.y - p.u);
                let pt_r = Point::new(center.x + p.v, center.y - p.u);
                self.fill_rect(Rect::new(pt_l, pt_r.onright().under()), color, alpha);
            }
        }

        let r = Rect::new(
            Point::new(center.x - radius, center.y + 1),
            Point::new(center.x + radius + 1, center.y + split + 1),
        );

        if self.viewport().contains(r) {
            for p in circle_points(radius).skip(1).take_while(|p| p.u < p.v) {
                let pt_l = Point::new(center.x - p.v, center.y + p.u);
                let pt_r = Point::new(center.x + p.v, center.y + p.u);
                self.fill_rect(Rect::new(pt_l, pt_r.onright().under()), color, alpha);
            }
        }

        let r = Rect::new(
            Point::new(center.x - radius, center.y + split),
            Point::new(center.x + radius + 1, center.y + radius + 1),
        );

        if self.viewport().contains(r) {
            for p in circle_points(radius) {
                if p.last {
                    let pt_l = Point::new(center.x - p.u, center.y + p.v);
                    let pt_r = Point::new(center.x + p.u, center.y + p.v);
                    self.fill_rect(Rect::new(pt_l, pt_r.onright().under()), color, alpha);
                }
            }
        }
    }

    /// Draws antialiased filled circle with the specified center and the
    /// radius.
    #[cfg(feature = "ui_antialiasing")]
    fn fill_circle(&mut self, center: Point, radius: i16, color: Color) {
        let split = unwrap!(circle_points(radius).last()).v;

        let alpha = 255;
        let alpha_mul = |a: u8| -> u8 { ((a as u16 * alpha as u16) / 255) as u8 };

        let r = Rect::new(
            Point::new(center.x - radius, center.y - radius),
            Point::new(center.x + radius + 1, center.y - split + 1),
        );

        if self.viewport().contains(r) {
            for p in circle_points(radius) {
                let pt_l = Point::new(center.x - p.u, center.y - p.v);
                let pt_r = Point::new(center.x + p.u, center.y - p.v);
                self.blend_pixel(pt_l, color, alpha_mul(p.frac));
                if pt_l != pt_r {
                    self.blend_pixel(pt_r, color, alpha_mul(p.frac));
                }

                if p.first {
                    let r = Rect::new(pt_l.onright(), pt_r.under());
                    self.fill_rect(r, color, alpha);
                }
            }
        }

        let r = Rect::new(
            Point::new(center.x - radius, center.y - split),
            Point::new(center.x + radius + 1, center.y + 1),
        );

        if self.viewport().contains(r) {
            for p in circle_points(radius).take_while(|p| p.u < p.v) {
                let pt_l = Point::new(center.x - p.v, center.y - p.u);
                let pt_r = Point::new(center.x + p.v, center.y - p.u);
                self.blend_pixel(pt_l, color, alpha_mul(p.frac));
                self.blend_pixel(pt_r, color, alpha_mul(p.frac));

                let r = Rect::new(pt_l.onright(), pt_r.under());
                self.fill_rect(r, color, alpha);
            }
        }

        let r = Rect::new(
            Point::new(center.x - radius, center.y + 1),
            Point::new(center.x + radius + 1, center.y + split + 1),
        );

        if self.viewport().contains(r) {
            for p in circle_points(radius).skip(1).take_while(|p| p.u < p.v) {
                let pt_l = Point::new(center.x - p.v, center.y + p.u);
                let pt_r = Point::new(center.x + p.v, center.y + p.u);
                self.blend_pixel(pt_l, color, alpha_mul(p.frac));
                self.blend_pixel(pt_r, color, alpha_mul(p.frac));

                let r = Rect::new(pt_l.onright(), pt_r.under());
                self.fill_rect(r, color, alpha);
            }
        }

        let r = Rect::new(
            Point::new(center.x - radius, center.y + split),
            Point::new(center.x + radius + 1, center.y + radius + 1),
        );

        if self.viewport().contains(r) {
            for p in circle_points(radius) {
                let pt_l = Point::new(center.x - p.u, center.y + p.v);
                let pt_r = Point::new(center.x + p.u, center.y + p.v);
                if pt_l != pt_r {
                    self.blend_pixel(pt_l, color, alpha_mul(p.frac));
                }
                self.blend_pixel(pt_r, color, alpha_mul(p.frac));

                if p.first {
                    let r = Rect::new(pt_l.onright(), pt_r.under());
                    self.fill_rect(r, color, alpha);
                }
            }
        }
    }

    /// Fills circle sector with a specified color.
    fn fill_sector(
        &mut self,
        center: Point,
        radius: i16,
        mut start: i16,
        mut end: i16,
        color: Color,
    ) {
        start = (PI4 * 8 + start % (PI4 * 8)) % (PI4 * 8);
        end = (PI4 * 8 + end % (PI4 * 8)) % (PI4 * 8);

        let alpha = 255;
        let alpha_mul = |a: u8| -> u8 { ((a as u16 * alpha as u16) / 255) as u8 };

        if start != end {
            // The algorithm fills everything except the middle point ;-)
            self.draw_pixel(center, color);
        }

        for octant in 0..8 {
            let angle = octant * PI4;

            // Function for calculation of 'u' coordinate inside the circle octant
            // radius * sin(angle)
            let sin = |angle: i16| -> i16 { sin_i16(angle, radius) };

            // Calculate the octant's bounding rectangle
            let p = Point::new(sin(PI4) + 1, -radius - 1).rot(octant);
            let r = Rect::new(center, p + center.into()).normalize();

            // Skip octant if not visible
            if !self.viewport().contains(r) {
                continue;
            }

            // Function for filling a line between two endpoints with antialiasing.
            // The function is special for each octant using 4 different axes of symmetry
            let filler = &mut |p1: Option<Point>, p1_frac, p2: Point, p2_frac| {
                let p2: Point = center + p2.rot(octant).into();
                self.blend_pixel(p2, color, alpha_mul(p2_frac));
                if let Some(p1) = p1 {
                    let p1: Point = center + p1.rot(octant).into();
                    let ofs = Point::new(-1, 0).rot(octant);
                    self.blend_pixel(p1 + ofs.into(), color, alpha_mul(p1_frac));
                    if ofs.x + ofs.y < 0 {
                        if ofs.x != 0 {
                            self.fill_rect(Rect::new(p1, p2.under()), color, alpha);
                        } else {
                            self.fill_rect(Rect::new(p1, p2.onright()), color, alpha);
                        }
                    } else {
                        let p1 = p1 + ofs.into();
                        let p2 = p2 + ofs.into();
                        if ofs.x != 0 {
                            self.fill_rect(Rect::new(p2, p1.under()), color, alpha);
                        } else {
                            self.fill_rect(Rect::new(p2, p1.onright()), color, alpha);
                        }
                    }
                }
            };

            let corr = if octant & 1 == 0 {
                // The clockwise octant
                |angle| angle
            } else {
                // The anticlockwise octant
                |angle| PI4 - angle
            };

            if start <= end {
                // Octant may contain 0 or 1 sector
                if start < angle + PI4 && end > angle {
                    if start <= angle && end >= angle + PI4 {
                        // Fill all pixels in the octant
                        fill_octant(radius, 0, sin(PI4), filler);
                    } else {
                        // Partial fill
                        let u1 = if start <= angle {
                            sin(corr(0))
                        } else {
                            sin(corr(start - angle))
                        };
                        let u2 = if end <= angle + PI4 {
                            sin(corr(end - angle))
                        } else {
                            sin(corr(PI4))
                        };

                        fill_octant(radius, u1, u2, filler);
                    }
                }
            } else {
                // Octant may contain 0, 1 or 2 sectors
                if end >= angle + PI4 || start <= angle {
                    // Fill all pixels in the octant
                    fill_octant(radius, 0, sin(PI4), filler);
                } else {
                    // Partial fill
                    if (end > angle) && (end < angle + PI4) {
                        // Fill up to `end`
                        fill_octant(radius, sin(corr(0)), sin(corr(end - angle)), filler);
                    }
                    if start < angle + PI4 {
                        // Fill all from `start`
                        fill_octant(radius, sin(corr(start - angle)), sin(corr(PI4)), filler);
                    }
                }
            }
        }
    }
}

/// Calculates endpoints of a single octant of a circle
///
/// Used internally by `Canvas::fill_sector()`.
fn fill_octant(
    radius: i16,
    mut u1: i16,
    mut u2: i16,
    fill: &mut impl FnMut(Option<Point>, u8, Point, u8),
) {
    // Starting end ending points on
    if u1 > u2 {
        (u1, u2) = (u2, u1);
    }

    let mut iter = circle_points(radius).skip(u1 as usize);

    // Intersection of the p1 line and the circle
    let p1_start = unwrap!(iter.next());

    // Intersection of the p1 line and the circle
    let mut p2_start = p1_start;

    loop {
        if let Some(p) = iter.next() {
            if p.u > u2 {
                break;
            }
            p2_start = p;
        } else {
            break;
        }
    }

    // Flag if we draw section up to 45degs
    let join_flag = iter.next().is_none();

    // Process area between a p1 line and the circle
    let mut p1_iter = line_points(p1_start.v, p1_start.u, 0);
    let mut first = true;
    let mut skip = 0;

    for c in circle_points(radius)
        .skip(p1_start.u as usize)
        .take((p2_start.u - p1_start.u) as usize)
    {
        let p2_coord = Point::new(c.u, -c.v);

        if c.first || first {
            let p1 = unwrap!(p1_iter.next());
            let p1_coord = Point::new(p1_start.u - p1.v, -p1_start.v + p1.u);
            first = false;

            fill(Some(p1_coord), p1.frac, p2_coord, c.frac);
        } else {
            fill(None, 0, p2_coord, c.frac);
        }

        skip = if c.last { 0 } else { 1 };
    }

    // Process area between a p1 and p2 lines
    let p2_iter = line_points(p2_start.v, p2_start.u, 0).skip(skip);
    for (p1, p2) in p1_iter.zip(p2_iter) {
        let p1_coord = Point::new(p1_start.u - p1.v, -p1_start.v + p1.u);
        let p2_coord = Point::new(p2_start.u - p2.v, -p2_start.v + p2.u);
        let p2_frac = if join_flag { 255 } else { 255 - p2.frac };
        fill(Some(p1_coord), p1.frac, p2_coord, p2_frac);
    }
}

impl Point {
    fn onleft(self) -> Self {
        Self {
            x: self.x - 1,
            ..self
        }
    }

    fn onright(self) -> Self {
        Self {
            x: self.x + 1,
            ..self
        }
    }

    fn above(self) -> Self {
        Self {
            y: self.y - 1,
            ..self
        }
    }

    fn under(self) -> Self {
        Self {
            y: self.y + 1,
            ..self
        }
    }

    fn rot(self, octant: i16) -> Self {
        let mut result = self;

        if (octant + 1) & 2 != 0 {
            result = Point::new(-result.y, -result.x);
        }

        if octant & 4 != 0 {
            result = Point::new(-result.x, result.y);
        }

        if (octant + 2) & 4 != 0 {
            result = Point::new(result.x, -result.y);
        }

        result
    }
}
