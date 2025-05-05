use core::{
    marker::PhantomData,
    mem::{align_of, size_of, MaybeUninit},
    ptr::NonNull,
};

pub use super::ffi::c_layout_t;

pub struct LayoutBuffer<T> {
    layout: NonNull<c_layout_t>,
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
        // SAFETY: the layout is non-null and properly aligned
        let buffer = unsafe { (*layout.as_ptr()).buf };

        let ptr = buffer.as_ptr();
        let addr = ptr as usize;

        // Check alignment and size
        let required_size = size_of::<T>();
        let required_align = align_of::<T>();
        if addr % required_align != 0 || buffer.len() < required_size {
            panic!("Buffer is not aligned or too small");
        }

        Self {
            layout,
            _marker: PhantomData,
        }
    }

    fn get_maybe_uninit(&self) -> &mut MaybeUninit<T> {
        // SAFETY: alignment and size are checked in `new()`
        let buffer = unsafe { (*self.layout.as_ptr()).buf };
        let layout = buffer.as_ptr() as *mut MaybeUninit<T>;
        // SAFETY: per safety assumptions of LayoutBuffer, we are allowed to mutably
        // borrow the memory.
        unsafe { &mut *layout }
    }

    /// Store a layout in the buffer.
    pub fn store(&self, value: T) {
        let layout = self.get_maybe_uninit();
        layout.write(value);
    }

    /// Get a mutable reference to the stored layout.
    ///
    /// # Safety
    ///
    /// Caller is responsible for ensuring that the buffer contains a valid
    /// layout -- that is, that `store()` has previously been called on the
    /// underlying pointer.
    pub unsafe fn get_mut(&self) -> &mut T {
        let layout = self.get_maybe_uninit();
        // SAFETY: safe under the safety assumptions of this function
        unsafe { layout.assume_init_mut() }
    }
}
