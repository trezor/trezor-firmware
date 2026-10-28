use core::sync::atomic::{AtomicU32, Ordering};

#[cfg(feature = "touch")]
use heapless::Vec;
use sys::time;
use without_alloc::alloc::LocalAllocLeakExt;

use crate::ui::component::Event;
use crate::ui::constant::screen;
use crate::ui::display::{self, Color};
#[cfg(feature = "touch")]
use crate::ui::event::TouchEvent;
use crate::ui::geometry::{Offset, Point, Rect};
use crate::ui::shape::{
    render_on_display, Canvas, DrawingCache, Renderer, Rgba8888Canvas, RotatedBar, Shape,
    ShapeClone,
};

pub trait ProdtestLayoutType {
    fn event(&mut self, event: Option<Event>) -> u32;
    fn show(&mut self) -> u32;
    fn init_welcome(id: Option<&'static str>) -> Self;
}

pub trait ProdtestUI {
    type CLayoutType: ProdtestLayoutType;

    fn screen_prodtest_show_text(text: &str);

    fn screen_prodtest_border();

    fn screen_prodtest_bars(colors: &str);

    #[cfg(feature = "touch")]
    fn screen_prodtest_touch(area: Rect);

    #[cfg(feature = "touch")]
    fn screen_prodtest_draw(events: Vec<TouchEvent, 256>);

    /// Draws a 2x2 grid of rotated rounded rectangles (filled, outlined,
    /// bordered, sharp) to exercise `RotatedBar` on the real display.
    ///
    /// Returns the time in microseconds spent drawing the shapes, without
    /// the display sync, background clear and refresh. On displays without
    /// a framebuffer, the shapes are only recorded at that point and drawn
    /// later, so the time is not meaningful there.
    fn screen_prodtest_shapes(angle: f32) -> u32 {
        display::sync();

        let mut shapes_time = 0;

        render_on_display(None, Some(Color::black()), |target| {
            // Wait for the background clear, it is not part of the shapes
            target.render_shape(Probe::Sync);
            let start = time::ticks_us();
            for shape in prodtest_shapes(angle) {
                shape.render(target);
            }
            shapes_time = (time::ticks_us() - start) as u32;
        });

        display::refresh();
        shapes_time
    }

    /// Draws the `prodtest_stripes()` animation at position `pos`.
    ///
    /// Returns the time in microseconds spent drawing the stripes, see
    /// `screen_prodtest_shapes()`.
    fn screen_prodtest_stripes(pos: u16) -> u32 {
        display::sync();

        let mut shapes_time = 0;

        render_on_display(None, Some(Color::black()), |target| {
            target.render_shape(Probe::Sync);
            let start = time::ticks_us();
            for stripe in prodtest_stripes(pos) {
                stripe.render(target);
            }
            shapes_time = (time::ticks_us() - start) as u32;
        });

        display::refresh();
        shapes_time
    }

    /// Measures the drawing primitives used by `RotatedBar` on the real
    /// framebuffer, see `Probe::bench()` for the meaning of the results.
    fn screen_prodtest_shapes_bench(results: &mut [u32; BENCH_RESULTS]) {
        display::sync();
        render_on_display(None, Some(Color::black()), |target| {
            target.render_shape(Probe::Bench);
        });
        display::refresh();

        for (r, b) in results.iter_mut().zip(BENCH.iter()) {
            *r = b.load(Ordering::Relaxed);
        }
    }
}

/// The shapes of `screen_prodtest_shapes()` rotated by `angle`.
fn prodtest_shapes(angle: f32) -> [RotatedBar; 4] {
    let area = screen();
    let cell = Offset::new(area.width() / 2, area.height() / 2);
    let size = Offset::new(cell.x * 3 / 4, cell.y * 3 / 8);
    let radius = size.y / 3;

    let center = |col: i16, row: i16| {
        area.top_left() + Offset::new(cell.x * col + cell.x / 2, cell.y * row + cell.y / 2)
    };
    let bar = |p: Point, a: f32| RotatedBar::new(Rect::from_center_and_size(p, size)).with_angle(a);

    [
        bar(center(0, 0), angle)
            .with_bg(Color::white())
            .with_radius(radius),
        bar(center(1, 0), -angle)
            .with_fg(Color::rgb(255, 64, 64))
            .with_thickness(3)
            .with_radius(radius),
        bar(center(0, 1), angle * 2.0)
            .with_fg(Color::white())
            .with_bg(Color::rgb(0, 96, 255))
            .with_thickness(4)
            .with_radius(radius),
        bar(center(1, 1), angle + 45.0).with_bg(Color::rgb(0, 255, 96)),
    ]
}

/// How far the stripes slide each way along their length, the animation
/// repeats after `4 * STRIPES_TRAVEL` pixels of movement.
const STRIPES_TRAVEL: i16 = 60;

/// Ten rounded stripes at 45 degrees covering the screen, sliding back and
/// forth along their length (diagonally), the odd ones in the opposite
/// direction to the even ones. `pos` is the distance moved since the start
/// of the animation, in pixels along each axis.
fn prodtest_stripes(pos: u16) -> [RotatedBar; 10] {
    let area = screen();
    let (w, h) = (area.width(), area.height());

    // Diagonal step between the stripes so that ten of them span the screen
    // perpendicularly to their length, (w + h) / sqrt(2)
    let step = (w + h) / 40 * 2;
    // Half of the step perpendicularly, step * sqrt(2) / 2
    let thickness = step * 7 / 10;
    let length = (w + h) * 8 / 15;

    // Triangle wave in -STRIPES_TRAVEL..=STRIPES_TRAVEL
    let t = (pos % (4 * STRIPES_TRAVEL) as u16) as i16;
    let shift = if t < 2 * STRIPES_TRAVEL {
        t - STRIPES_TRAVEL
    } else {
        3 * STRIPES_TRAVEL - t
    };

    core::array::from_fn(|i| {
        let k = (2 * i as i16 - 9) * step / 2;
        let s = if i % 2 == 0 { shift } else { -shift };
        let center = area.center() + Offset::new(k + s, s - k);
        RotatedBar::new(Rect::from_center_and_size(
            center,
            Offset::new(length, thickness),
        ))
        .with_angle(45.0)
        .with_radius(thickness / 2)
        .with_bg(Color::white())
    })
}

pub const BENCH_RESULTS: usize = 14;

static BENCH: [AtomicU32; BENCH_RESULTS] = [const { AtomicU32::new(0) }; BENCH_RESULTS];

/// A pseudo-shape giving direct access to the canvas.
#[derive(Clone, Copy)]
enum Probe {
    /// Waits for pending DMA operations on the canvas
    Sync,
    /// Runs `bench()`
    Bench,
}

impl Probe {
    /// Number of repetitions of the cheap operations
    const N: u32 = 1000;
    /// Number of repetitions of the band fills
    const M: u32 = 100;

    /// Fills `BENCH` with:
    /// - 0: wait for the background clear [us]
    /// - 1: `draw_pixel()` [ns]
    /// - 2: `blend_pixel()` [ns]
    /// - 3: 1x1 `fill_rect()`, back to back [ns]
    /// - 4: 1x1 `fill_rect()` followed by a `draw_pixel()` [ns]
    /// - 5: 142x1 `fill_rect()` followed by a `draw_pixel()` [ns]
    /// - 6: 142x16 `fill_rect()` followed by a `draw_pixel()` [ns]
    /// - 7: one distance evaluation of `RotatedBar` [ns]
    /// - 8..=11: each shape of `screen_prodtest_shapes(30)` [us]
    /// - 12: `draw_pixel()` into a small bitmap in regular RAM [ns]
    /// - 13: `blend_pixel()` into a small bitmap in regular RAM [ns]
    fn bench(canvas: &mut dyn Canvas, cache: &DrawingCache) {
        let measure = |f: &mut dyn FnMut()| {
            let start = time::ticks_us();
            f();
            (time::ticks_us() - start) as u32
        };
        // Spread the pixels over a few rows, away from the shapes' edges
        let pt = |i: u32| Point::new((i % 300) as i16, 10 + (i / 300) as i16);
        let white = Color::white();
        let mut result = [0u32; BENCH_RESULTS];

        result[0] = measure(&mut || canvas.draw_pixel(Point::zero(), Color::black()));
        result[1] = measure(&mut || {
            for i in 0..Self::N {
                canvas.draw_pixel(pt(i), white);
            }
        }) * 1000
            / Self::N;
        result[2] = measure(&mut || {
            for i in 0..Self::N {
                canvas.blend_pixel(pt(i), white, 128);
            }
        }) * 1000
            / Self::N;
        result[3] = measure(&mut || {
            for i in 0..Self::N {
                canvas.fill_rect(
                    Rect::from_top_left_and_size(pt(i), Offset::uniform(1)),
                    white,
                    255,
                );
            }
            canvas.draw_pixel(Point::zero(), white);
        }) * 1000
            / Self::N;
        result[4] = measure(&mut || {
            for i in 0..Self::N {
                canvas.fill_rect(
                    Rect::from_top_left_and_size(pt(i), Offset::uniform(1)),
                    white,
                    255,
                );
                canvas.draw_pixel(pt(i + 1), white);
            }
        }) * 1000
            / Self::N;
        result[5] = measure(&mut || {
            for i in 0..Self::N {
                let r = Rect::from_top_left_and_size(
                    Point::new(0, 20 + (i % 100) as i16),
                    Offset::new(142, 1),
                );
                canvas.fill_rect(r, white, 255);
                canvas.draw_pixel(Point::zero(), white);
            }
        }) * 1000
            / Self::N;
        result[6] = measure(&mut || {
            for i in 0..Self::M {
                let r = Rect::from_top_left_and_size(
                    Point::new(0, 20 + (i % 10) as i16 * 16),
                    Offset::new(142, 16),
                );
                canvas.fill_rect(r, white, 255);
                canvas.draw_pixel(Point::zero(), white);
            }
        }) * 1000
            / Self::M;
        let mut sum = 0.0;
        result[7] =
            measure(&mut || sum = prodtest_shapes(30.0)[0].bench_dist(Self::N)) * 1000 / Self::N;
        core::hint::black_box(sum);

        canvas.fill_background(Color::black());
        for (r, mut shape) in result[8..].iter_mut().zip(prodtest_shapes(30.0)) {
            *r = measure(&mut || {
                shape.draw(canvas, cache);
                // Include the DMA operations the shape left pending
                canvas.draw_pixel(Point::zero(), Color::black());
            });
        }

        // The same pixel writes outside of the framebuffer
        let mut buf = [0u8; 64 * 4 * 4];
        let mut ram = unwrap!(Rgba8888Canvas::new(
            Offset::new(64, 4),
            None,
            None,
            &mut buf[..]
        ));
        let ram_pt = |i: u32| Point::new((i % 64) as i16, (i / 64 % 4) as i16);
        result[12] = measure(&mut || {
            for i in 0..Self::N {
                ram.draw_pixel(ram_pt(i), white);
            }
        }) * 1000
            / Self::N;
        result[13] = measure(&mut || {
            for i in 0..Self::N {
                ram.blend_pixel(ram_pt(i), white, 128);
            }
        }) * 1000
            / Self::N;

        for (b, r) in BENCH.iter().zip(result) {
            b.store(r, Ordering::Relaxed);
        }
    }
}

impl Shape<'_> for Probe {
    fn bounds(&self) -> Rect {
        screen()
    }

    fn cleanup(&mut self, _cache: &DrawingCache) {}

    fn draw(&mut self, canvas: &mut dyn Canvas, cache: &DrawingCache) {
        match self {
            Probe::Sync => canvas.draw_pixel(Point::zero(), Color::black()),
            Probe::Bench => Self::bench(canvas, cache),
        }
    }
}

impl<'s> ShapeClone<'s> for Probe {
    fn clone_at_bump<T>(self, bump: &'s T) -> Option<&'s mut dyn Shape<'s>>
    where
        T: LocalAllocLeakExt<'s>,
    {
        let clone = bump.alloc_t()?;
        Some(clone.uninit.init(self))
    }
}
