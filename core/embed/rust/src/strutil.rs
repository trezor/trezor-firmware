use heapless::String;

#[cfg(feature = "micropython")]
use crate::error::Error;

#[cfg(feature = "micropython")]
use crate::micropython::{buffer::StrBuffer, obj::Obj};

#[cfg(feature = "translations")]
use crate::translations::TR;

/// Trait for slicing off string prefix by a specified number of bytes.
/// See `StringType` for deeper explanation.
pub trait SkipPrefix {
    fn skip_prefix(&self, bytes: usize) -> Self;
}

// XXX only implemented in bootloader, as we don't want &str to satisfy
// StringType in the main firmware. This is because we want to avoid duplication
// of every StringType-parametrized component.
#[cfg(feature = "bootloader")]
impl SkipPrefix for &str {
    fn skip_prefix(&self, chars: usize) -> Self {
        &self[chars..]
    }
}

/// Trait for internal representation of strings.
/// Exists so that we can support `StrBuffer` as well as `&str` in the UI
/// components. Implies the following operations:
/// - dereference into a short-lived `&str` reference (AsRef<str>)
/// - create a new string by skipping some number of bytes (SkipPrefix) - used
///   when rendering continuations of long strings
/// - create a new string from a string literal (From<&'static str>)
pub trait StringType:
    AsRef<str> + From<&'static str> + Into<TString<'static>> + SkipPrefix
{
}

impl<T> StringType for T where
    T: AsRef<str> + From<&'static str> + Into<TString<'static>> + SkipPrefix
{
}

/// Unified-length String type, long enough for most simple use-cases.
pub type ShortString = String<50>;

pub fn hexlify(data: &[u8], buffer: &mut [u8]) {
    const HEX_LOWER: [u8; 16] = *b"0123456789abcdef";
    let mut i: usize = 0;
    for b in data.iter().take(buffer.len() / 2) {
        let hi: usize = ((b & 0xf0) >> 4).into();
        let lo: usize = (b & 0x0f).into();
        buffer[i] = HEX_LOWER[hi];
        buffer[i + 1] = HEX_LOWER[lo];
        i += 2;
    }
}

pub fn format_i64(num: i64, buffer: &mut [u8]) -> Option<&str> {
    let mut i = 0;
    let mut num = num;
    let negative = if num < 0 {
        num = -num;
        true
    } else {
        false
    };

    while num > 0 && i < buffer.len() {
        buffer[i] = b'0' + ((num % 10) as u8);
        num /= 10;
        i += 1;
    }
    match i {
        0 => Some("0"),
        _ if num > 0 => None,
        _ if negative && i == buffer.len() => None,
        _ => {
            if negative {
                buffer[i] = b'-';
                i += 1;
            }
            let result = &mut buffer[..i];
            result.reverse();
            Some(unsafe { core::str::from_utf8_unchecked(result) })
        }
    }
}

#[derive(Copy, Clone)]
pub enum TString<'a> {
    #[cfg(feature = "micropython")]
    Allocated(StrBuffer),
    #[cfg(feature = "translations")]
    Translation(TR),
    Str(&'a str),
}

impl TString<'_> {
    pub fn is_empty(&self) -> bool {
        self.map(|s| s.is_empty())
    }

    pub fn map<F, T>(&self, fun: F) -> T
    where
        F: for<'a> FnOnce(&'a str) -> T,
        T: 'static,
    {
        match self {
            #[cfg(feature = "micropython")]
            Self::Allocated(buf) => fun(buf.as_ref()),
            #[cfg(feature = "translations")]
            Self::Translation(tr) => tr.map_translated(fun),
            Self::Str(s) => fun(s),
        }
    }
}

impl TString<'static> {
    #[cfg(feature = "translations")]
    pub const fn from_translation(tr: TR) -> Self {
        Self::Translation(tr)
    }

    #[cfg(feature = "micropython")]
    pub const fn from_strbuffer(buf: StrBuffer) -> Self {
        Self::Allocated(buf)
    }

    pub const fn empty() -> Self {
        Self::Str("")
    }
}

impl<'a> TString<'a> {
    pub const fn from_str(s: &'a str) -> Self {
        Self::Str(s)
    }
}

impl<'a> From<&'a str> for TString<'a> {
    fn from(s: &'a str) -> Self {
        Self::Str(s)
    }
}

#[cfg(feature = "translations")]
impl From<TR> for TString<'static> {
    fn from(tr: TR) -> Self {
        Self::from_translation(tr)
    }
}

#[cfg(feature = "micropython")]
impl From<StrBuffer> for TString<'static> {
    fn from(buf: StrBuffer) -> Self {
        Self::from_strbuffer(buf)
    }
}

#[cfg(feature = "micropython")]
impl TryFrom<Obj> for TString<'static> {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        Ok(StrBuffer::try_from(obj)?.into())
    }
}

#[cfg(feature = "micropython")]
impl<'a> TryFrom<TString<'a>> for Obj {
    type Error = Error;

    fn try_from(s: TString<'a>) -> Result<Self, Self::Error> {
        s.map(|t| t.try_into())
    }
}
