use core::{convert::TryFrom, ops::Deref, ptr, slice, str};

use crate::ui::component::text::paragraphs::ParagraphStrType;

/// Represents an immutable UTF-8 string managed by MicroPython GC.
/// This either means static data, or a valid GC object.
///
/// # Safety
///
/// We assume that MicroPython is handling strings according to Python
/// semantics, i.e., that string data is immutable.
/// Furthermore, we assume that string data is always either static or a GC head
/// pointer, i.e., we can never obtain a pointer into the middle of a GC string.
///
/// Given the above assumptions about MicroPython strings, working with
/// StrBuffers in Rust is safe.
///
/// The `off` field represents offset from the `ptr` and allows us to do
/// substring slices while keeping the head pointer as required by GC.
#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct StrBuffer {
    ptr: *const u8,
    len: u16,
    off: u16,
}

impl StrBuffer {
    pub fn empty() -> Self {
        Self::from("")
    }

    fn as_bytes(&self) -> &[u8] {
        if self.ptr.is_null() {
            &[]
        } else {
            unsafe { slice::from_raw_parts(self.ptr.add(self.off.into()), self.len.into()) }
        }
    }

    pub fn offset(&self, skip_bytes: usize) -> Self {
        let off: u16 = unwrap!(skip_bytes.try_into());
        assert!(off <= self.len);
        assert!(self.as_ref().is_char_boundary(skip_bytes));
        Self {
            ptr: self.ptr,
            // Does not overflow because `off <= self.len`.
            len: self.len - off,
            // `self.off + off` could only overflow if `self.off + self.len` could overflow, and
            // given that `off` only advances by as much as `len` decreases, that should not be
            // possible either.
            off: self.off + off,
        }
    }
}

impl Default for StrBuffer {
    fn default() -> Self {
        Self::empty()
    }
}

impl Deref for StrBuffer {
    type Target = str;

    fn deref(&self) -> &Self::Target {
        self.as_ref()
    }
}

impl AsRef<str> for StrBuffer {
    fn as_ref(&self) -> &str {
        // SAFETY:
        // - If constructed from a Rust `&str`, this is safe.
        unsafe { str::from_utf8_unchecked(self.as_bytes()) }
    }
}

impl From<&'static str> for StrBuffer {
    fn from(val: &'static str) -> Self {
        Self {
            ptr: val.as_ptr(),
            len: unwrap!(val.len().try_into()),
            off: 0,
        }
    }
}

impl ParagraphStrType for StrBuffer {
    fn skip_prefix(&self, chars: usize) -> Self {
        self.offset(chars)
    }
}
