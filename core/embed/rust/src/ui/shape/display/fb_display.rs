#[cfg(feature = "display_mono")]
use crate::ui::shape::canvas::Mono8Canvas;
#[cfg(feature = "display_rgb565")]
use crate::ui::shape::canvas::Rgb565Canvas;
#[cfg(feature = "display_rgba8888")]
use crate::ui::shape::canvas::Rgba8888Canvas;

use crate::{
    trezorhal::display::{self, XFrameBuffer},
    ui::{
        display::Color,
        geometry::Offset,
        shape::{DirectRenderer, DrawingCache},
    },
};

use super::{base::Display, bumps};

macro_rules! direct_display {
    ($name:ident, $canvas:ident) => {
        pub struct $name;

        impl Display for $name {
            type Canvas<'canvas> = $canvas<'canvas>;
            type Renderer<'env, 'canvas, 'bump> = DirectRenderer<'env, 'bump, $canvas<'canvas>>
                            where
                                'canvas: 'env;

            fn display_canvas<'canvas, 'fb>(
                framebuffer: &'canvas mut XFrameBuffer<'fb>,
            ) -> Self::Canvas<'canvas> {
                let width = display::DISPLAY_RESX as i16;
                let height = display::DISPLAY_RESY as i16;

                unwrap!(Self::Canvas::new(
                    Offset::new(width, height),
                    Some(framebuffer.stride()),
                    None,
                    framebuffer.buf()
                ))
            }

            fn renderer<'env, 'canvas, 'bumps>(
                bumps: &'bumps bumps::Bumps<'bumps>,
                canvas: &'env mut Self::Canvas<'canvas>,
                bg_color: Color,
            ) -> Self::Renderer<'env, 'canvas, 'bumps>
            where
                'canvas: 'env,
            {
                let cache = DrawingCache::new(bumps);
                Self::Renderer::new(canvas, Some(bg_color), cache)
            }
        }
    };
}

#[cfg(feature = "display_mono")]
direct_display!(Mono8, Mono8Canvas);
#[cfg(feature = "display_rgb565")]
direct_display!(Rgb565, Rgb565Canvas);
#[cfg(feature = "display_rgba8888")]
direct_display!(Rgba8888, Rgba8888Canvas);
