#[cfg(all(feature = "xframebuffer", feature = "display_mono"))]
pub mod fb_mono8;
#[cfg(all(feature = "xframebuffer", feature = "display_mono"))]
pub use fb_mono8::render_on_display;

#[cfg(feature = "display_rgb565")]
pub mod nofb_rgb565;
#[cfg(all(not(feature = "xframebuffer"), feature = "display_rgb565"))]
pub use nofb_rgb565::render_on_display;

#[cfg(all(feature = "xframebuffer", feature = "display_rgb565"))]
pub mod fb_rgb565;
#[cfg(all(
    feature = "xframebuffer",
    feature = "display_rgb565",
    not(feature = "display_rgba8888")
))]
pub use fb_rgb565::render_on_display;

#[cfg(all(feature = "xframebuffer", feature = "display_rgba8888",))]
pub mod fb_rgba8888;
#[cfg(all(
    feature = "xframebuffer",
    feature = "display_rgba8888",
    not(feature = "display_rgb565")
))]
pub use fb_rgba8888::render_on_display;

pub mod fake_display;
#[cfg(not(feature = "new_rendering"))]
pub use fake_display::render_on_display;
