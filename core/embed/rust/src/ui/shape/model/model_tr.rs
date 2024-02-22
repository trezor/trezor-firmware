use crate::ui::{
    canvas::{BasicCanvas, Canvas, Mono8Canvas, Viewport},
    display,
    display::Color,
    geometry::{Offset, Rect},
    shape::{DirectRenderer, DrawingCache},
};

use static_alloc::Bump;

pub fn render_on_display<'a, F>(clip: Option<Rect>, bg_color: Option<Color>, func: F)
where
    F: FnOnce(&mut DirectRenderer<'_, 'a, Mono8Canvas<'a>>),
{
    // TODO: do not use constants 128 & 64 directly

    static mut FRAME_BUFFER: [u8; 128 * 64] = [0u8; 128 * 64];

    let fb = &mut unsafe { &mut *core::ptr::addr_of_mut!(FRAME_BUFFER) }[..];

    static mut BUMP: Bump<[u8; 40 * 1024]> = Bump::uninit();

    let bump = unsafe { &mut *core::ptr::addr_of_mut!(BUMP) };
    {
        bump.reset();

        let cache = DrawingCache::new(bump, bump);
        let mut canvas = unwrap!(Mono8Canvas::new(Offset::new(128, 64), None, fb));

        if let Some(clip) = clip {
            canvas.set_viewport(Viewport::new(clip));
        }

        let mut target = DirectRenderer::new(&mut canvas, bg_color, &cache);

        func(&mut target);

        refresh_display(&canvas);
    }
}

fn refresh_display(canvas: &Mono8Canvas) {
    // TODO: optimize

    display::set_window(canvas.bounds());

    let view = canvas.view();

    for y in 0..canvas.size().y {
        let row = unwrap!(view.row(y));
        for value in row.iter() {
            let c = Color::rgb(*value, *value, *value);
            display::pixeldata(c.into());
        }
    }

    display::refresh();
}
