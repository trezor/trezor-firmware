use core::{marker::PhantomData, mem::MaybeUninit, ptr::NonNull};

pub use super::ffi::c_layout_t;

pub struct LayoutBuffer<T> {
    layout: NonNull<MaybeUninit<T>>,
    _marker: PhantomData<T>,
}

impl<T> LayoutBuffer<T> {
    /// Create a new `LayoutBuffer` from an underlying buffer.
    ///
    /// # Safety
    ///
    /// Caller must ensure that the buffer can be held mutably for the lifetime
    /// of the `LayoutBuffer`.
    pub unsafe fn new(buffer: *mut c_layout_t) -> Self {
        let layout = unwrap!(NonNull::new(buffer));
        // SAFETY: c_layout_t is just an array of u8 which is always aligned
        let buffer = unsafe { &mut (*layout.as_ptr()).buf };

        // SAFETY: buffer is just an array of u8 which we are slicing.
        let (_, aligned, _) = unsafe { buffer.align_to_mut::<MaybeUninit<T>>() };

        let slot = aligned.first_mut();

        let slot = unwrap!(slot, "Cannot align buffer or buffer is too small");

        // SAFETY: we ensured that slot is non-null and valid
        let layout = unsafe { NonNull::new_unchecked(slot as *mut _) };
        Self {
            layout,
            _marker: PhantomData,
        }
    }

    fn get_maybe_uninit(&mut self) -> &mut MaybeUninit<T> {
        // SAFETY: we ensured in `new()` that `ptr` is valid for the lifetime
        // of the buffer and properly aligned.
        unsafe { &mut *self.layout.as_ptr() }
    }

    /// Store a layout in the buffer.
    pub fn store(&mut self, value: T) {
        self.get_maybe_uninit().write(value);
    }

    /// Get a mutable reference to the stored layout.
    ///
    /// # Safety
    ///
    /// Caller is responsible for ensuring that the buffer contains a valid
    /// layout -- that is, that `store()` has previously been called on the
    /// underlying pointer.
    pub unsafe fn get_mut(&mut self) -> &mut T {
        let layout = self.get_maybe_uninit();
        // SAFETY: safe under the safety assumptions of this function
        unsafe { layout.assume_init_mut() }
    }
}
