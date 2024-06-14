use heapless::String;

#[cfg(feature = "micropython")]
use crate::error::Error;

#[cfg(feature = "micropython")]
use crate::micropython::{buffer::StrBuffer, obj::Obj};

#[cfg(feature = "translations")]
use crate::translations::TR;

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
    Translation {
        tr: TR,
        offset: u16,
    },
    Str(&'a str),
}

impl TString<'_> {
    pub fn len(&self) -> usize {
        self.map(|s| s.len())
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }

    /// Maps the string to a value using a closure.
    ///
    /// # Safety
    ///
    /// The properties of this function are bounded by the properties of
    /// `TranslatedString::map_translated`. The reference to the string is
    /// guaranteed to be valid throughout the closure, but must not escape
    /// it. The `for<'a>` bound on the closure's argument ensures this.
    pub fn map<F, T>(&self, fun: F) -> T
    where
        F: for<'a> FnOnce(&'a str) -> T,
    {
        match self {
            #[cfg(feature = "micropython")]
            Self::Allocated(buf) => fun(buf.as_ref()),
            #[cfg(feature = "translations")]
            Self::Translation { tr, offset } => tr.map_translated(|s| fun(&s[*offset as usize..])),
            Self::Str(s) => fun(s),
        }
    }

    pub fn skip_prefix(&self, skip_bytes: usize) -> Self {
        self.map(|s| {
            assert!(skip_bytes <= s.len());
            assert!(s.is_char_boundary(skip_bytes));
        });
        match self {
            #[cfg(feature = "micropython")]
            Self::Allocated(s) => Self::Allocated(s.skip_prefix(skip_bytes)),
            #[cfg(feature = "translations")]
            Self::Translation { tr, offset } => Self::Translation {
                tr: *tr,
                offset: offset + skip_bytes as u16,
            },
            Self::Str(s) => Self::Str(&s[skip_bytes..]),
        }
    }
}

impl TString<'static> {
    #[cfg(feature = "translations")]
    pub const fn from_translation(tr: TR) -> Self {
        Self::Translation { tr, offset: 0 }
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

impl<'a, 'b> PartialEq<TString<'a>> for TString<'b> {
    fn eq(&self, other: &TString<'a>) -> bool {
        self.map(|s| other.map(|o| s == o))
    }
}

impl Eq for TString<'_> {}

impl ufmt::uDisplay for TString<'_> {
    fn fmt<W>(&self, f: &mut ufmt::Formatter<'_, W>) -> Result<(), W::Error>
    where
        W: ufmt::uWrite + ?Sized,
    {
        self.map(|s| f.write_str(s))
    }
}

#[cfg(feature = "debug")]
impl ufmt::uDebug for TString<'_> {
    fn fmt<W>(&self, f: &mut ufmt::Formatter<'_, W>) -> Result<(), W::Error>
    where
        W: ufmt::uWrite + ?Sized,
    {
        match self {
            #[cfg(feature = "micropython")]
            TString::Allocated(buf) => {
                f.write_str("Allocated(")?;
                buf.fmt(f)?;
                f.write_str(")")?;
            }
            #[cfg(feature = "translations")]
            TString::Translation { tr, offset } => {
                f.write_str("Translation(")?;
                tr.fmt(f)?;
                f.write_str(", ")?;
                offset.fmt(f)?;
                f.write_str(")")?;
            }
            TString::Str(s) => {
                f.write_str("Str(")?;
                f.write_str(s)?;
                f.write_str(")")?;
            }
        }
        Ok(())
    }
}
