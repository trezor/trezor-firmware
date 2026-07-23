use crate::app_runtime2;

pub use crate::traits::util::Timeout;

impl Timeout {
    /// Converts this timeout to an absolute deadline by adding it to the current systick.
    pub fn as_deadline(&self) -> u32 {
        app_runtime2::systick_ms().wrapping_add(self.0)
    }

    /// Blocks until this timeout elapses.
    pub fn sleep(&self) {
        app_runtime2::sleep(self.0);
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
