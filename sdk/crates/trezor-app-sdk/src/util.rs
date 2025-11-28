use ufmt::derive::uDebug;

use crate::{low_level_api, sysevent::SysEvents};

#[derive(uDebug, Copy, Clone, PartialEq, Eq)]
pub struct Timeout(u32);

pub const TIMEOUT_MAX: u32 = u32::MAX / 2 - 1;

impl Timeout {
    pub fn ms(ms: u32) -> Self {
        assert!(ms <= TIMEOUT_MAX, "Timeout too long");
        Self(ms)
    }

    pub fn seconds(seconds: u32) -> Self {
        Self::ms(seconds * 1000)
    }

    pub fn minutes(minutes: u32) -> Self {
        Self::seconds(minutes * 60)
    }

    pub fn max() -> Self {
        Self::ms(TIMEOUT_MAX)
    }

    pub fn as_deadline(&self) -> u32 {
        low_level_api::systick_ms().wrapping_add(self.0)
    }

    pub fn sleep(&self) {
        let awaited = SysEvents::empty();
        awaited.poll(*self);
    }
}

pub struct SliceWriter<'a> {
    slice: &'a mut [u8],
    pos: usize,
}

impl<'a> SliceWriter<'a> {
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
