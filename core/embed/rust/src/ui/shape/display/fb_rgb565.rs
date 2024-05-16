use crate::ui::{
    display::Color,
    geometry::Offset,
    shape::{BasicCanvas, DirectRenderer, DrawingCache, Renderer, Rgb565Canvas, Viewport},
};

use crate::trezorhal::display;

use static_alloc::Bump;

const BUMP_A_SIZE: usize = DrawingCache::get_bump_a_size();
const BUMP_B_SIZE: usize = DrawingCache::get_bump_b_size();

/// Runs a user-defined function with two bump allocators.
///
/// The function is passed two bump allocators, `bump_a` and `bump_b`, which
/// can be used to allocate memory for temporary objects.
///
/// The function calls cannot be nested. The function panics if that happens.
fn run_with_bumps<F>(func: F)
where
    F: FnOnce(&mut Bump<[u8; BUMP_A_SIZE]>, &mut Bump<[u8; BUMP_B_SIZE]>),
{
    // TODO: check if the function call is nested and panic

    #[cfg_attr(not(target_os = "macos"), link_section = ".no_dma_buffers")]
    static mut BUMP_A: Bump<[u8; BUMP_A_SIZE]> = Bump::uninit();

    #[cfg_attr(not(target_os = "macos"), link_section = ".buf")]
    static mut BUMP_B: Bump<[u8; BUMP_B_SIZE]> = Bump::uninit();

    let bump_a = unsafe { &mut *core::ptr::addr_of_mut!(BUMP_A) };
    let bump_b = unsafe { &mut *core::ptr::addr_of_mut!(BUMP_B) };

    bump_a.reset();
    bump_b.reset();

    func(bump_a, bump_b);
}

type ConcreteRenderer<'a, 'alloc> = DirectRenderer<'a, 'alloc, Rgb565Canvas<'alloc>>;

pub struct ScopedRenderer<'a, 'alloc, 'env>
where
    'env: 'alloc,
{
    pub renderer: ConcreteRenderer<'a, 'alloc>,
    _env: core::marker::PhantomData<&'env mut &'env ()>,
}

impl<'alloc> Renderer<'alloc> for ScopedRenderer<'_, 'alloc, '_> {
    fn viewport(&self) -> Viewport {
        self.renderer.viewport()
    }

    fn set_viewport(&mut self, viewport: Viewport) {
        self.renderer.set_viewport(viewport);
    }

    fn render_shape<S>(&mut self, shape: S)
    where
        S: crate::ui::shape::Shape<'alloc> + crate::ui::shape::ShapeClone<'alloc> {
        self.renderer.render_shape(shape);
    }
}

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
pub fn render_on_display<'env, F>(viewport: Option<Viewport>, bg_color: Option<Color>, func: F)
where
    F: for<'alloc> FnOnce(&mut ScopedRenderer<'_, 'alloc, 'env>),
{
    run_with_bumps(|bump_a, bump_b| {
        let width = display::DISPLAY_RESX as i16;
        let height = display::DISPLAY_RESY as i16;

        let cache = DrawingCache::new(bump_a, bump_b);

        let (fb, fb_stride) = display::get_frame_buffer();

        let mut canvas = unwrap!(Rgb565Canvas::new(
            Offset::new(width, height),
            Some(fb_stride),
            None,
            fb
        ));

        if let Some(viewport) = viewport {
            canvas.set_viewport(viewport);
        }

        let mut scoped = ScopedRenderer {
            renderer: DirectRenderer::new(&mut canvas, bg_color, &cache),
            _env: core::marker::PhantomData,
        };
        func(&mut scoped);
    });
}

// pub fn render_on_canvas<'c, 'env, F>(canvas: &'c mut Rgb565Canvas, bg_color: Option<Color>, func: F)
// where
//     F: for<'alloc> FnOnce(&mut ScopedRenderer<'c, 'alloc, 'env>),
// {
//     run_with_bumps(|bump_a, bump_b| {
//         let cache = DrawingCache::new(bump_a, bump_b);
//         let mut scoped = ScopedRenderer {
//             renderer: DirectRenderer::new(canvas, bg_color, &cache),
//             _env: core::marker::PhantomData,
//         };
//         func(&mut scoped);
//     });
// }
