use core::{
    ops::{Deref, DerefMut},
    ptr,
};

use super::ffi;

pub use ffi::TEXT_BUFFER_HEIGHT;

macro_rules! buffer_wrapper {
    ($rust_name: ident, $type: ident, $get: ident, $free: ident) => {
        pub struct $rust_name(ptr::NonNull<ffi::$type>);

        impl $rust_name {
            pub fn get() -> Self {
                unsafe {
                    let ptr = ffi::$get(false);
                    Self(unwrap!(ptr::NonNull::new(ptr)))
                }
            }

            pub fn get_cleared() -> Self {
                unsafe {
                    let ptr = ffi::$get(true);
                    Self(unwrap!(ptr::NonNull::new(ptr)))
                }
            }
        }

        impl Deref for $rust_name {
            type Target = ffi::$type;

            fn deref(&self) -> &Self::Target {
                // SAFETY: The lifetime of the pointer is 'static and the C API
                // promises that we are the sole owner.
                unsafe { self.0.as_ref() }
            }
        }

        impl DerefMut for $rust_name {
            fn deref_mut(&mut self) -> &mut Self::Target {
                // SAFETY: The lifetime of the pointer is 'static and the C API
                // promises that we are the sole owner, and we have borrowed mutably.
                unsafe { self.0.as_mut() }
            }
        }

        impl Drop for $rust_name {
            fn drop(&mut self) {
                unsafe {
                    ffi::$free(self.0.as_mut());
                }
            }
        }
    };
}

buffer_wrapper!(
    BufferLine16bpp,
    buffer_line_16bpp_t,
    buffers_get_line_16bpp,
    buffers_free_line_16bpp
);
buffer_wrapper!(
    BufferLine4bpp,
    buffer_line_4bpp_t,
    buffers_get_line_4bpp,
    buffers_free_line_4bpp
);
buffer_wrapper!(
    BufferText,
    buffer_text_t,
    buffers_get_text,
    buffers_free_text
);
buffer_wrapper!(
    BufferBlurring,
    buffer_blurring_t,
    buffers_get_blurring,
    buffers_free_blurring
);
buffer_wrapper!(
    BufferBlurringTotals,
    buffer_blurring_totals_t,
    buffers_get_blurring_totals,
    buffers_free_blurring_totals
);
#[cfg(feature = "jpeg")]
buffer_wrapper!(
    BufferJpeg,
    buffer_jpeg_t,
    buffers_get_jpeg,
    buffers_free_jpeg
);
#[cfg(feature = "jpeg")]
buffer_wrapper!(
    BufferJpegWork,
    buffer_jpeg_work_t,
    buffers_get_jpeg_work,
    buffers_free_jpeg_work
);
