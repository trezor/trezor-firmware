use ufmt::derive::uDebug;

use crate::low_level_api;
use crate::sysevent::SysEvents;

/// Represents a timeout duration in milliseconds.
///
/// Use [`Timeout::max`] for the longest supported timeout, or construct
/// via [`Timeout::ms`], [`Timeout::seconds`], or [`Timeout::minutes`].
#[derive(uDebug, Copy, Clone, PartialEq, Eq)]
pub struct Timeout(u32);

pub const TIMEOUT_MAX: u32 = u32::MAX / 2 - 1;

impl Timeout {
    /// Creates a timeout of `ms` milliseconds.
    ///
    /// # Panics
    ///
    /// Panics if `ms` exceeds [`TIMEOUT_MAX`].
    pub fn ms(ms: u32) -> Self {
        assert!(ms <= TIMEOUT_MAX, "Timeout too long");
        Self(ms)
    }

    /// Creates a timeout of `seconds` seconds.
    ///
    /// # Panics
    ///
    /// Panics if the resulting timeout exceeds [`TIMEOUT_MAX`] ms.
    pub fn seconds(seconds: u32) -> Self {
        Self::ms(seconds * 1000)
    }

    /// Creates a timeout of `minutes` minutes.
    ///
    /// # Panics
    ///
    /// Panics if the resulting timeout exceeds [`TIMEOUT_MAX`] ms.
    pub fn minutes(minutes: u32) -> Self {
        Self::seconds(minutes * 60)
    }

    /// Returns the maximum supported timeout value.
    pub fn max() -> Self {
        Self::ms(TIMEOUT_MAX)
    }

    /// Converts this timeout to an absolute deadline by adding it to the current systick.
    pub fn as_deadline(&self) -> u32 {
        low_level_api::systick_ms().wrapping_add(self.0)
    }

    /// Blocks until this timeout elapses.
    pub fn sleep(&self) {
        let awaited = SysEvents::empty();
        awaited.poll(*self);
    }
}

/// A fixed-capacity writer over a mutable byte slice, implementing [`ufmt::uWrite`].
///
/// Useful for formatting into stack-allocated buffers without heap allocation.
pub struct SliceWriter<'a> {
    slice: &'a mut [u8],
    pos: usize,
}

impl<'a> SliceWriter<'a> {
    /// Creates a new `SliceWriter` backed by `slice`.
    pub fn new(slice: &'a mut [u8]) -> Self {
        Self { slice, pos: 0 }
    }
}

impl<'a> ufmt::uWrite for SliceWriter<'a> {
    type Error = ();

    fn write_str(&mut self, s: &str) -> Result<(), Self::Error> {
        if self.pos + s.len() > self.slice.len() {
            return Err(());
        }
        self.slice[self.pos..self.pos + s.len()].copy_from_slice(s.as_bytes());
        self.pos += s.len();
        Ok(())
    }
}

impl<'a> AsRef<str> for SliceWriter<'a> {
    fn as_ref(&self) -> &str {
        // SAFETY: The only way to write is by invoking the ufmt::uWrite impl,
        // which appends valid Rust &strs.
        unsafe { core::str::from_utf8_unchecked(&self.slice[..self.pos]) }
    }
}
