use core::ops::DerefMut;
use core::pin::Pin;

use crate::memory::{Memory, ZeroableMemory};

pub trait RawHasher: ZeroableMemory {
    type Digest;

    unsafe fn update(ctx: *mut Self, data: &[u8]);
    unsafe fn finalize(ctx: *mut Self, output: &mut Self::Digest);
}

pub trait Hasher {
    type Digest;

    fn update(&mut self, data: &[u8]);
    fn finalize(&mut self, output: &mut Self::Digest);
}

pub struct PinnedHasher<H> {
    ctx: Pin<H>,
}

impl<H, D> PinnedHasher<D>
where
    H: RawHasher,
    D: DerefMut<Target = Memory<H>>,
{
    pub fn new_uninit(ctx: Pin<D>) -> Self {
        Self { ctx }
    }

    /// Get the raw pointer to the hasher context.
    ///
    /// # Safety
    ///
    /// TODO
    pub(crate) unsafe fn inner(&mut self) -> *mut H {
        unsafe { self.ctx.as_mut().inner() }
    }

    pub fn memory() -> Memory<H> {
        Memory::default()
    }

    pub fn update(&mut self, data: &[u8]) {
        unsafe {
            H::update(self.inner(), data);
        }
    }

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
