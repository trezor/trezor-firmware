use core::{marker::PhantomPinned, mem::MaybeUninit, pin::Pin};

use zeroize::{zeroize_flat_type, Zeroize};

/// Wrapper for a memory used as a context by C functions. Its purpose is to be
/// !Unpin, thus prevent moves when accessed through a Pin. We want to avoid
/// moves as they can leave cryptographic data in memory.
///
/// T needs to be a plain struct that is valid when zeroed.
pub struct Memory<T> {
    inner: T,
    _phantom: PhantomPinned,
}

impl<T> Default for Memory<T> {
    fn default() -> Self {
        // SAFETY: a zeroed block of memory is valid for C functions
        let inner = unsafe { MaybeUninit::<T>::zeroed().assume_init() };
        Self {
            inner,
            _phantom: PhantomPinned,
        }
    }
}

impl<T> Zeroize for Memory<T> {
    fn zeroize(&mut self) {
        // SAFETY:
        // - contains no references
        // - plain struct with not Drop impls
        // - only called in Drop impl
        // - zeroed block of memory is valid
        unsafe { zeroize_flat_type(&mut self.inner as *mut T) };
    }
}

type PinnedMemory<'a, T> = Pin<&'a mut Memory<T>>;

impl<T> Memory<T> {
    // SAFETY:
    // The caller must ensure that the return value is handled according to the
    // contract of `Pin::map_unchecked_mut` and `Pin::get_unchecked_mut`.
    // Notably passing the pointer to a C function should be fine since the notion
    // of moving doesn't exist there and the entire point of this pinning is not
    // to leak more data than the C implementation.
    pub unsafe fn inner(self: &mut Pin<&mut Self>) -> *mut T {
        unsafe {
            self.as_mut()
                .map_unchecked_mut(|m| &mut m.inner)
                .get_unchecked_mut()
        }
    }
}

impl<T> Zeroize for Pin<&mut Memory<T>> {
    fn zeroize(&mut self) {
        // SAFETY: `Memory::zeroize` does not do any moving
        unsafe {
            self.as_mut().get_unchecked_mut().zeroize();
        }
    }
}

/// Initializes backing memory on the stack and passes it to a constructor.
/// The macro is basically a specialized version of `core::pin::pin!` for use
/// with Memory<T>.
#[allow(unused_macros)]
macro_rules! init_ctx {
    ($type:ty, $name:ident $(, $arg:expr)*) => {
        // assign the backing memory to $name...
        let mut $name = <$type>::memory();
        // ... then make it inaccessible by overwriting the binding, and pin it
        // SAFETY: The value is pinned: it is the local above which cannot be named outside this macro.
        #[allow(unused_mut)]
        let mut $name = unsafe {
            <$type>::new(core::pin::Pin::new_unchecked(&mut $name), $($arg),*)
        };
    };
}

pub(crate) use init_ctx;
