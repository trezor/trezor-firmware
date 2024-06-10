mod bumps;
mod direct_canvas;

pub use direct_canvas::render_on_canvas;

pub mod fake_display;
#[cfg(all(feature = "xframebuffer", feature = "display_mono"))]
pub mod fb_mono8;
#[cfg(all(feature = "xframebuffer", feature = "display_rgb565"))]
pub mod fb_rgb565;
#[cfg(all(feature = "xframebuffer", feature = "display_rgba8888",))]
pub mod fb_rgba8888;
#[cfg(feature = "display_rgb565")]
pub mod nofb_rgb565;

#[cfg(not(feature = "new_rendering"))]
mod _new_rendering {
    pub use super::fake_display::render_on_display;
}

#[cfg(feature = "new_rendering")]
mod _new_rendering {
    #[cfg(not(feature = "xframebuffer"))]
    mod _xframebuffer {
        #[cfg(feature = "display_rgb565")]
        pub use super::super::nofb_rgb565::render_on_display;

        #[cfg(not(feature = "display_rgb565"))]
        pub use super::super::fake_display::render_on_display;
    }

    #[cfg(feature = "xframebuffer")]
    mod _xframebuffer {
        #[cfg(feature = "display_rgb565")]
        pub use super::super::fb_rgb565::render_on_display;

        #[cfg(all(feature = "display_rgba8888", not(feature = "display_rgb565")))]
        pub use super::super::fb_rgba8888::render_on_display;

        #[cfg(all(
            feature = "display_mono",
            not(feature = "display_rgb565"),
            not(feature = "display_rgba8888")
        ))]
        pub use super::super::fb_mono8::render_on_display;
    }

    pub use _xframebuffer::render_on_display;
}

pub use _new_rendering::render_on_display;

pub use bumps::unlock_bumps_on_failure;
