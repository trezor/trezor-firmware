use core::hint::black_box;
use core::marker::PhantomPinned;
use core::mem::MaybeUninit;
use core::ops::{Deref, DerefMut};

use zeroize::{Zeroize, ZeroizeOnDrop, zeroize_flat_type};

/// Marker trait for C types that can be safely zeroed.
///
/// # Safety
///
/// Must only be implemented for types for which all-zero memory is a valid
/// value, such as structs consumed by C.
pub unsafe trait ZeroableMemory {}

/// Zeroizing wrapper around sensitive memory contexts.
///
/// Implements zeroize-on-drop behavior, provides a Default all-zero value, and
/// it is !Unpin, so that it can be correctly used inside a Pin.
///
/// It also gates all access to the sensitive context behind "hazardous" calls.
///
/// T needs to be a plain struct that is valid when zeroed.
///
/// This wrapper type should be used together with [`SecretContextLock`]:
/// allocate memory of type `SecretContext<T>`, then pass it on to its users
/// wrapped in a `SecretContextLock`.
///
/// # Copy hazard
///
/// `SecretContext` is designed to wrap cryptographic contexts and other
/// sensitive memory. When operating on such values naively, Rust is allowed by
/// design to make copies of the sensitive data as it moves around memory.
///
/// This wrapper, by itself, does not (and cannot) prevent this behavior. Its
/// role is to make it visible to callers, via using the only accessor
/// [`SecretContext::hazard_mut`].
///
/// See [`SecretContextLock`] for proper usage in a struct.
#[repr(transparent)]
pub struct SecretContext<T: ZeroableMemory> {
    inner: T,
    _phantom: PhantomPinned,
}

impl<T: ZeroableMemory> Default for SecretContext<T> {
    fn default() -> Self {
        // SAFETY: T is ZeroableMemory, so a zeroed block of memory is valid
        let inner = unsafe { MaybeUninit::<T>::zeroed().assume_init() };
        Self {
            inner,
            _phantom: PhantomPinned,
        }
    }
}

impl<T: ZeroableMemory> Drop for SecretContext<T> {
    fn drop(&mut self) {
        self.zeroize();
    }
}

impl<T: ZeroableMemory> ZeroizeOnDrop for SecretContext<T> {}

impl<T: ZeroableMemory> SecretContext<T> {
    /// Get a mutable reference to the wrapped value.
    ///
    /// # Copy hazard
    ///
    /// You are responsible for not copying out the value (either manually or
    /// via something like `mem::replace`).
    pub fn hazard_mut(&mut self) -> &mut T {
        black_box(&mut self.inner)
    }

    /// Zeroize the wrapped value.
    pub fn zeroize(&mut self) {
        // SAFETY:
        // - zeroed block of memory is valid
        unsafe { zeroize_flat_type(&mut self.inner as *mut T) };
    }
}

impl<T: ZeroableMemory> Zeroize for SecretContext<T> {
    /// Zeroize the wrapped value.
    fn zeroize(&mut self) {
        Self::zeroize(self);
    }
}

/// Exclusive lock over a [`SecretContext`].
///
/// Holds a `DerefMut` to a [`SecretContext`] (typically `&mut
/// SecretContext<T>`) so that no other code can move or copy the context while
/// the lock is alive. On drop, the pointed-to context is zeroized — even when
/// dropping the lock does not drop the context itself, which is the case for
/// `&mut`.
///
/// Wrap a hasher or similar type around `SecretContextLock` so that:
/// * sensitive state is not copied by the wrapper
/// * nobody else can observe the context while it is in use
/// * the context is zeroized as soon as exclusive access is released
///
/// # Copy hazard
///
/// Protects from hazardous calls which rely on the caller not copying out the
/// sensitive context.
///
/// You are responsible for not copying out the value obtained through
/// [`SecretContextLock::hazard_mut`]. Prefer [`SecretContextLock::guarded`]
/// and implementing the operation on [`HazardGuard`], which moves that
/// responsibility from the call site to the operation itself.
///
/// # Example
///
/// ```ignore
/// struct Hasher<D: DerefMut<Target = SecretContext<Ctx>>>(SecretContextLock<D>);
///
/// impl<D: DerefMut<Target = SecretContext<Ctx>>> Hasher<D> {
///     fn new(ctx: D) -> Self {
///         Self(SecretContextLock::new(ctx))
///     }
/// }
/// ```
#[repr(transparent)]
pub struct SecretContextLock<D>(D)
where
    D: DerefMut,
    <D as Deref>::Target: Zeroize;

impl<D, T> SecretContextLock<D>
where
    D: DerefMut<Target = SecretContext<T>>,
    T: ZeroableMemory,
{
    /// Lock `ctx` for exclusive use until this value is dropped.
    pub fn new(ctx: D) -> Self {
        Self(black_box(ctx))
    }

    /// Get a mutable reference to the wrapped value.
    ///
    /// # Copy hazard
    ///
    /// You are responsible for not copying out the value (either manually or
    /// via something like `mem::replace`).
    pub fn hazard_mut(&mut self) -> &mut T {
        black_box(self.0.hazard_mut())
    }

    /// Get a [`HazardGuard`] for the enclosed `SecretContext`.
    ///
    /// Operations on the sensitive context are implemented as methods of
    /// `HazardGuard`, so that they can only ever run on a locked context.
    pub fn guarded(&mut self) -> HazardGuard<'_, T> {
        HazardGuard(black_box(&mut self.0))
    }
}

/// Witness of exclusive in-place access to a [`SecretContext`].
///
/// A `HazardGuard` can be constructed in two ways:
///
/// * hazard-free, via [`SecretContextLock::guarded`].
/// * hazardously via [`HazardGuard::hazard_new`].
///
/// Operations on a sensitive context -- typically FFI calls taking a pointer to
/// it -- should be implemented as methods of `HazardGuard`. Such an operation
/// then cannot be invoked on an unprotected context, and its callers do not
/// need to uphold anything by hand.
///
/// # Copy hazard
///
/// A method of `HazardGuard` must operate on the context in place. It is the
/// responsibility of the implementation not to copy the context out (either
/// manually or via something like `mem::replace`).
///
/// The method [`HazardGuard::hazard_new`] intentionally overrides the copy
/// hazard protection, exposing the guarded operations to hazard.
#[repr(transparent)]
pub struct HazardGuard<'a, T: ZeroableMemory>(&'a mut SecretContext<T>);

impl<'a, T: ZeroableMemory> HazardGuard<'a, T> {
    /// Construct a new `HazardGuard` from a mutable reference to a
    /// `SecretContext`.
    ///
    /// # Copy hazard
    ///
    /// Constructing a `HazardGuard` this way bypasses hazard protection
    /// guarantees. This method is only provided as an escape hatch for contexts
    /// where a [`SecretContextLock`] cannot be used.
    pub fn hazard_new(ctx: &'a mut SecretContext<T>) -> Self {
        Self(black_box(ctx))
    }

    /// Get a mutable reference to the guarded value, for passing to FFI.
    ///
    /// # Copy hazard
    ///
    /// You are responsible for not copying out the value (either manually or
    /// via something like `mem::replace`).
    pub fn hazard_mut(&mut self) -> &mut T {
        black_box(self.0.hazard_mut())
    }
}

impl<D> Drop for SecretContextLock<D>
where
    D: DerefMut,
    <D as Deref>::Target: Zeroize,
{
    fn drop(&mut self) {
        // Zeroize through the DerefMut so that `&mut SecretContext` is cleared
        // when exclusive access ends, not only when the context itself is dropped.
        self.0.zeroize();
    }
}

impl<D> ZeroizeOnDrop for SecretContextLock<D>
where
    D: DerefMut,
    <D as Deref>::Target: Zeroize,
{
}
