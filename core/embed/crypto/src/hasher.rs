use core::ops::DerefMut;
use core::pin::Pin;

use crate::memory::{Memory, ZeroableMemory};

/// Raw C hasher context operated on through a pointer.
pub trait RawHasher: ZeroableMemory {
    type Digest;

    /// # Safety
    ///
    /// `ctx` must point to an initialized context.
    unsafe fn update(ctx: *mut Self, data: &[u8]);
    /// # Safety
    ///
    /// `ctx` must point to an initialized context.
    unsafe fn finalize(ctx: *mut Self, output: &mut Self::Digest);
}

/// Incremental hasher writing its digest into a caller-provided buffer.
pub trait Hasher {
    type Digest;

    fn update(&mut self, data: &[u8]);
    fn finalize(&mut self, output: &mut Self::Digest);
}

/// Hasher over a pinned [`Memory`] context, so the context is never moved.
pub struct PinnedHasher<H> {
    ctx: Pin<H>,
}

impl<H, D> PinnedHasher<D>
where
    H: RawHasher,
    D: DerefMut<Target = Memory<H>>,
{
    /// Wraps a pinned context. The context is not initialized here.
    pub fn new_uninit(ctx: Pin<D>) -> Self {
        Self { ctx }
    }

    /// Get the raw pointer to the hasher context.
    ///
    /// # Safety
    ///
    /// The pointer must only be passed to C and never used to move the
    /// context.
    pub(crate) unsafe fn inner(&mut self) -> *mut H {
        unsafe { self.ctx.as_mut().inner() }
    }

    /// Creates zeroed backing memory for the context.
    pub fn memory() -> Memory<H> {
        Memory::default()
    }

    /// Feeds `data` into the hasher.
    pub fn update(&mut self, data: &[u8]) {
        unsafe {
            H::update(self.inner(), data);
        }
    }

    /// Writes the digest into `output`.
    pub fn finalize(&mut self, output: &mut H::Digest) {
        unsafe {
            H::finalize(self.inner(), output);
        }
    }
}

impl<H, D> Hasher for PinnedHasher<D>
where
    H: RawHasher,
    D: DerefMut<Target = Memory<H>>,
{
    type Digest = H::Digest;

    fn update(&mut self, data: &[u8]) {
        Self::update(self, data);
    }

    fn finalize(&mut self, output: &mut Self::Digest) {
        Self::finalize(self, output);
    }
}
