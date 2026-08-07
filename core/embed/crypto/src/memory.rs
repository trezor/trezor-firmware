use core::marker::PhantomPinned;
use core::mem::MaybeUninit;
use core::ops::{Deref, DerefMut};
use core::pin::Pin;

use zeroize::zeroize_flat_type;

/// Marker trait for C types that can be safely zeroed.
///
/// # Safety
///
/// Must only be implemented for types for which all-zero memory is a valid
/// value, such as structs consumed by C.
pub unsafe trait ZeroableMemory {}

/// Wrapper for a memory used as a context by C functions. Its purpose is to be
/// !Unpin, thus prevent moves when accessed through a Pin. We want to avoid
/// moves as they can leave cryptographic data in memory.
///
/// T needs to be a plain struct that is valid when zeroed.
#[repr(transparent)]
pub struct Memory<T: ZeroableMemory> {
    inner: T,
    _phantom: PhantomPinned,
}

impl<T: ZeroableMemory> Default for Memory<T> {
    fn default() -> Self {
        // SAFETY: a zeroed block of memory is valid for C functions
        let inner = unsafe { MaybeUninit::<T>::zeroed().assume_init() };
        Self {
            inner,
            _phantom: PhantomPinned,
        }
    }
}

impl<T: ZeroableMemory> Drop for Memory<T> {
    fn drop(&mut self) {
        self.zeroize();
    }
}

impl<T: ZeroableMemory> Memory<T> {
    /// Projection shortcut to the wrapped value.
    ///
    /// # Safety
    ///
    /// This method is a shortcut for `Pin::get_unchecked_mut().inner`,
    /// so all safety requirements for `get_unchecked_mut` apply.
    pub unsafe fn inner<'a>(self: &'a mut Pin<&mut Self>) -> &'a mut T {
        let s = unsafe { self.as_mut().get_unchecked_mut() };
        &mut s.inner
    }

    /// Zeroize the wrapped value.
    pub fn zeroize(&mut self) {
        // SAFETY:
        // - zeroed block of memory is valid
        unsafe { zeroize_flat_type(&mut self.inner as *mut T) };
    }
}

impl<T: ZeroableMemory> Deref for Memory<T> {
    type Target = T;

    fn deref(&self) -> &Self::Target {
        &self.inner
    }
}

impl<T: ZeroableMemory> DerefMut for Memory<T> {
    fn deref_mut(&mut self) -> &mut Self::Target {
        &mut self.inner
    }
}

impl<T: ZeroableMemory> AsRef<T> for Memory<T> {
    fn as_ref(&self) -> &T {
        &self.inner
    }
}

impl<T: ZeroableMemory> AsMut<T> for Memory<T> {
    fn as_mut(&mut self) -> &mut T {
        &mut self.inner
    }
}

/// Initializes backing memory on the stack.
///
/// Specialized shorthand version of `core::pin::pin!` for use with [`Memory`],
///
/// ```ignore
/// init_ctx!(ctx);
/// // is the same as:
/// // let ctx = pin!(Memory::default());
///
/// let mut sha = sha256_new(ctx_name);
/// ```
///
#[macro_export]
macro_rules! init_ctx {
    ($name:ident) => { let $name = ::core::pin::pin!($crate::memory::Memory::default()); };
}

pub use init_ctx;
