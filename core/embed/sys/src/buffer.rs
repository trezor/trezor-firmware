//! Owned raw buffers that the kernel may write into.
//!
//! [`KernelBuffer`] claims a [`KernelBufferPtr`] (a borrowed slice or, with
//! `alloc`, a `Box<[T]>`) so no Rust references to the memory remain while the
//! kernel owns it, and frees that pointer on drop.

use core::marker::PhantomData;
use core::ops::DerefMut;

/// Trait for pointers that can move to the kernel and back.
///
/// Typical usage:
///
/// 1. [`Self::claim`] consumes `self` and transfers ownership of the pointed-to
///    buffer into a raw pointer. This ensures that, e.g., no live references to
///    the memory exist in Rust while it is owned by the kernel.
/// 2. The buffer is passed to the kernel as a raw pointer.
/// 3. After unregistering from the kernel, [`Self::free`] will free the
///    associated memory.
///
/// Two implementations are provided:
/// - `&mut [T]` for static or stack-allocated buffers. `claim()` is a simple
///   cast to a raw pointer and `free()` does nothing.
/// - `Box<[T]>` if feature `alloc` is enabled, for heap-allocated buffers.
///   `claim()` deconstructs the `Box` and `free()` reconstructs it in order to
///   drop it.
///
/// [`KernelBuffer`] runs this sequence automatically: it claims on
/// construction and frees on drop. The caller is responsible for registering
/// and unregistering the buffer with the kernel in between.
///
/// # Safety
///
/// The sequence of `claim()`/`free()` must be sound:
///
/// 1. [`Self::claim`] deconstructs `self` without freeing it, and returns a raw
///    pointer to some memory.
/// 2. This memory remains valid until [`Self::free`] is called.
/// 3. [`Self::free`], given a raw pointer previously returned by
///    [`Self::claim`], correctly frees the memory according to the pointer
///    type.
pub unsafe trait KernelBufferPtr: DerefMut<Target = [Self::Align]> + Sized {
    /// Element type of the buffer slice.
    ///
    /// Used as the alignment unit: a `[usize]` buffer is aligned to
    /// `size_of::<usize>()`, which the kernel requires for IPC.
    type Align;

    /// Claims the pointed-to buffer.
    ///
    /// That is, consumes the pointer, returning it as a raw pointer. The buffer
    /// must remain valid until [`Self::free`] is called.
    ///
    /// Implementers must take care not to invalidate the memory when `self` is
    /// dropped at the end of `claim()`'s scope.
    fn claim(self) -> *mut [Self::Align];

    /// Frees memory previously claimed by [`Self::claim`].
    ///
    /// # Safety
    ///
    /// `ptr` must be a raw pointer previously returned by [`Self::claim`].
    unsafe fn free(ptr: *mut [Self::Align]);
}

/// Stack or static buffers. Claiming is a pointer cast; freeing is a no-op
/// because this type does not own the allocation.
unsafe impl<T> KernelBufferPtr for &mut [T] {
    type Align = T;

    fn claim(self) -> *mut [Self::Align] {
        self as *mut _
    }

    unsafe fn free(_ptr: *mut [Self::Align]) {
        // do nothing
    }
}

#[cfg(feature = "alloc")]
mod alloc {
    extern crate alloc;

    use alloc::boxed::Box;

    use super::KernelBufferPtr;

    /// Heap-allocated buffers. Claiming uses [`Box::into_raw`]; freeing
    /// reconstructs the `Box` so the allocator can reclaim the memory.
    unsafe impl<T> KernelBufferPtr for Box<[T]> {
        type Align = T;

        fn claim(self) -> *mut [Self::Align] {
            Box::into_raw(self)
        }

        unsafe fn free(ptr: *mut [Self::Align]) {
            // reconstruct the original Box, just to immediately drop it and
            // reclaim the memory.
            // SAFETY: caller must provide the same ptr that came from `claim()`
            drop(unsafe { Box::from_raw(ptr) });
        }
    }
}

/// A buffer whose storage has been claimed for kernel use.
///
/// Constructed with [`Self::new`], which consumes a [`KernelBufferPtr`] and
/// holds only a raw pointer. Dropping the `KernelBuffer` calls
/// [`KernelBufferPtr::free`].
///
/// The original pointer type is kept as `P` so drop can free the right kind of
/// storage, and so a borrowed `&mut [T]` cannot outlive its referent.
///
/// Accessors return raw pointers only: creating a Rust reference while the
/// kernel may write the buffer would be undefined behavior.
pub struct KernelBuffer<P: KernelBufferPtr> {
    ptr: *mut [P::Align],
    _marker: PhantomData<P>,
}

impl<P: KernelBufferPtr> KernelBuffer<P> {
    /// Claims `ptr` and wraps the resulting raw pointer.
    ///
    /// While `ptr` is claimed, it should not be possible to create Rust
    /// references to the buffer.
    ///
    /// Caller must unregister the buffer from the kernel before the
    /// `KernelBuffer` is dropped.
    pub fn new(ptr: P) -> Self {
        Self {
            ptr: ptr.claim(),
            _marker: PhantomData,
        }
    }

    /// Pointer to the buffer, as a C-compatible pointer to first element.
    ///
    /// Length is not part of this pointer; use [`Self::len`] or
    /// [`Self::byte_size`] together with it when calling into C.
    pub const fn ptr(&self) -> *mut P::Align {
        self.ptr as *mut _
    }

    /// Number of [`KernelBufferPtr::Align`] elements in the buffer.
    pub const fn len(&self) -> usize {
        self.ptr.len()
    }

    /// Size of the buffer in bytes (`len * size_of::<Align>()`).
    pub const fn byte_size(&self) -> usize {
        self.len() * core::mem::size_of::<P::Align>()
    }

    /// Whether the buffer has zero elements.
    pub const fn is_empty(&self) -> bool {
        self.len() == 0
    }

    /// Fat pointer to the whole slice, including length.
    pub const fn fat_ptr(&self) -> *mut [P::Align] {
        self.ptr as *mut _
    }
}

impl<P: KernelBufferPtr> Drop for KernelBuffer<P> {
    fn drop(&mut self) {
        // SAFETY: we are handing in the same ptr we got from `claim()`,
        // via `new()`.
        unsafe { P::free(self.ptr) };
    }
}

// SAFETY: kernel_buffer uniquely owns memory that was a `P: Send` (e.g.
// Box<[usize]>). Kernel writes do not make the allocation !Send.
unsafe impl<P: KernelBufferPtr + Send> Send for KernelBuffer<P> {}
