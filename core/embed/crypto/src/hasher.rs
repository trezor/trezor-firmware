use core::ops::DerefMut;
use core::pin::Pin;

/// Raw implementation of the hasher interface.
///
/// Should be implemented directly on the respective C context struct.
///
/// # Safety
///
/// `RawHasher` methods accept a simple `&mut self` pointer. Such pointer can go
/// anywhere, including to an owned value on the stack. While the call itself is
/// sound, mismanaging the pointed-to value can leave copies of internal state
/// in memory, which should be avoided.
///
/// In order to use `RawHasher` safely, the caller must ensure that the
/// pointed-to value is not moved or copied -- a guarantee analogous to
/// `!Unpin`.
pub trait RawHasher {
    /// The type of the digest produced by the hasher.
    ///
    /// Should be a fixed-size array of bytes.
    type Digest: AsRef<[u8]>;

    /// Hash the data into the hasher state.
    ///
    /// # Safety
    ///
    /// The caller must ensure that the pointed-to value is not moved or copied
    /// -- a guarantee analogous to `!Unpin`.
    unsafe fn update_raw(&mut self, data: &[u8]);

    /// Finalize the hasher state and return the digest.
    ///
    /// # Safety
    ///
    /// The caller must ensure that the pointed-to value is not moved or copied
    /// -- a guarantee analogous to `!Unpin`.
    unsafe fn finalize_raw(&mut self) -> Self::Digest;
}

/// Hasher interface.
///
/// Provides methods for adding data to the hasher (`update()`) and calculating
/// the digest (`finalize()`).
///
/// Should be implemented on a wrapping pointer to a `RawHasher`, such as `Pin`.
///
/// # Safety
///
/// MUST NOT be implemented on a raw C context struct (see [`RawHasher`] for
/// why).
pub trait Hasher {
    /// The type of the digest produced by the hasher.
    ///
    /// Should be a fixed-size array of bytes.
    type Digest: AsRef<[u8]>;

    /// Hash the data into the hasher state.
    fn update(&mut self, data: &[u8]);

    /// Finalize the hasher state and return the digest.
    fn finalize(&mut self) -> Self::Digest;
}

/// Pinned wrapper around a `RawHasher`.
///
/// A generic wrapper around a `RawHasher` type, providing a safe `Hasher`
/// interface, by pinning the underlying context.
///
/// Typically not used directly, you want to call one of the shorthand
/// constructors like [`sha256_new`] instead, which also invoke the appropriate
/// initializer method.
pub struct PinnedHasher<D>(Pin<D>);

impl<H, D> PinnedHasher<D>
where
    D: DerefMut<Target = H>,
    H: RawHasher,
{
    /// Create a new `PinnedHasher` from a pinned context.
    ///
    /// # Safety
    ///
    /// Caller is responsible for initializing the context before using the
    /// hasher methods.
    pub unsafe fn new_no_init(ctx: Pin<D>) -> Self {
        Self(ctx)
    }

    /// Hash the data into the wrapped hasher state.
    pub fn update(&mut self, data: &[u8]) {
        // SAFETY:
        // get_unchecked_mut: update_raw does not invalidate the pin
        // update_raw: safe on pinned memory
        unsafe { self.0.as_mut().get_unchecked_mut().update_raw(data) }
    }

    /// Finalize the hasher state and return the digest.
    pub fn finalize(&mut self) -> H::Digest {
        // SAFETY:
        // get_unchecked_mut: finalize_raw does not invalidate the pin
        // finalize_raw: safe on pinned memory
        unsafe { self.0.as_mut().get_unchecked_mut().finalize_raw() }
    }
}

impl<H, D> Hasher for PinnedHasher<D>
where
    D: DerefMut<Target = H>,
    H: RawHasher,
{
    type Digest = H::Digest;

    fn update(&mut self, data: &[u8]) {
        Self::update(self, data)
    }

    fn finalize(&mut self) -> Self::Digest {
        Self::finalize(self)
    }
}
