use crate::{
    trezorhal::display::XFrameBuffer,
    ui::{
        display::Color,
        shape::{BasicCanvas, Renderer},
    },
};

use super::bumps::Bumps;

pub trait Display {
    type Canvas<'canvas>: BasicCanvas;
    type Renderer<'env, 'canvas, 'bump>: Renderer<'bump>
    where
        'canvas: 'env;

    // given a framebuffer whose backing memory is 'fb, provide a Canvas<'a>,
    // indicating that it is shorter-lived than the 'fb memory; namely, it lives
    // as long as the scope in which the _owner_ of the 'fb memory exists
    fn display_canvas<'canvas, 'fb>(
        framebuffer: &'canvas mut XFrameBuffer<'fb>,
    ) -> Self::Canvas<'canvas>;

    // given:
    // * bumps whose backing memory is 'alloc
    // * drawing cache whose backing memory is also 'alloc (because it is based on
    //   bumps)
    // * canvas whose backing memory is 'canvas (that is, one shorter than 'fb of
    //   the framebuffer owner)
    // whose owners all live in 'a
    // return a Renderer that is as long-lived as said scope, i.e., 'a
    fn renderer<'env, 'canvas, 'bumps>(
        bumps: &'bumps Bumps<'bumps>,
        canvas: &'env mut Self::Canvas<'canvas>,
        bg_color: Color,
    ) -> Self::Renderer<'env, 'canvas, 'bumps>
    where
        'canvas: 'env;
}

macro_rules! render_on_display {
    ($display:ty, $color:expr, $closure:expr) => {{
        use $crate::{
            trezorhal::display::XFrameBuffer,
            ui::shape::display::{base::Display, bumps::Bumps},
        };

        let bumps = Bumps::lock();
        let mut framebuffer = XFrameBuffer::lock();
        let mut canvas = <$display as Display>::display_canvas(&mut framebuffer);
        let mut renderer = <$display as Display>::renderer(&bumps, &mut canvas, $color);
        $closure(&mut renderer);
    }};
}
pub(crate) use render_on_display;
