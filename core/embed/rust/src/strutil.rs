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

/// Formats a BLE pairing code as a zero-padded string with spaces between
/// digits. Adds an extra space after the 3rd digit for improved readability.
/// Example: code=123, width=6 produces "0 0 0   1 2 3"
pub fn format_pairing_code(code: u32, width: usize) -> ShortString {
    let mut buf = [0; 20];
    let code_str = unwrap!(format_i64(code as _, &mut buf));

    let mut formatted_code = ShortString::new();
    let padding = width.saturating_sub(code_str.len());

    for i in 0..width {
        let c = if i < padding {
            '0'
        } else {
            unwrap!(code_str.chars().nth(i - padding))
        };
        unwrap!(formatted_code.push(c));
        if i < width - 1 {
            unwrap!(formatted_code.push(' '));
            if i == (width / 2 - 1) {
                // extra space in the middle
                unwrap!(formatted_code.push(' '));
            }
        }
    }

    formatted_code
}

/// Selects the correct plural form from a template string based on a count.
///
/// The `template` is a `&str` containing 2 or 3 variants separated by `|`:
/// - 2 forms: "singular|plural" (e.g., `"day|days"`)
/// - 3 forms: "singular|few|many" (e.g., `"den|dny|dnů"` for Czech)
///
/// # Arguments
/// * `template` - A pipe-separated string with plural forms.
/// * `count` - The numeric count to select the correct plural form.
///
/// # Returns
/// A `ShortString` containing the correct plural form, or an empty
/// `ShortString` if the template is malformed or conversion fails.
pub fn plural_form(template: &str, count: u32) -> ShortString {
    // If no separator found, return the whole template (fallback behavior)
    if !template.contains('|') {
        return ShortString::try_from(template).unwrap_or_default();
    }

    // Split the template by '|' into components
    let mut parts = template.split('|');

    // Get the required first two parts
    let (first, second) = match (parts.next(), parts.next()) {
        (Some(first), Some(second)) => (first, second),
        _ => return ShortString::default(),
    };
    // Third form (many), optional
    let third = parts.next();

    // Choose appropriate form based on `count`
    let selected = match third {
        Some(many) => {
            // Czech-style: 1 → singular, 2–4 → few, 0 or ≥5 → many
            if count == 1 {
                first
            } else if (2..=4).contains(&count) {
                second
            } else {
                many
            }
        }
        None => {
            // Simple fallback: 1 → singular, all others → plural
            if count == 1 {
                first
            } else {
                second
            }
        }
    };

    // Convert safely, returning empty string on failure
    ShortString::try_from(selected).unwrap_or_default()
}

#[derive(Copy, Clone)]
#[cfg_attr(test, derive(Debug))]
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
            Self::Translation { tr, offset } => {
                // Avoid slicing translated strings, since they are loaded from flash and may
                // change later. See https://github.com/trezor/trezor-firmware/pull/5685#discussion_r2316266438 for more details.
                debug_assert_eq!(skip_bytes, 0);
                Self::Translation {
                    tr: *tr,
                    offset: offset + skip_bytes as u16,
                }
            }
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

#[cfg(test)]
mod tests {

    #[test]
    fn test_format_code() {
        use super::format_pairing_code;
        let width = 6;
        // Test normal cases with different digit counts
        assert_eq!(format_pairing_code(123, width).as_str(), "0 0 0  1 2 3");
        assert_eq!(format_pairing_code(7, width).as_str(), "0 0 0  0 0 7");
        assert_eq!(format_pairing_code(123456, width).as_str(), "1 2 3  4 5 6");

        // Test boundary cases
        assert_eq!(format_pairing_code(0, width).as_str(), "0 0 0  0 0 0");
        assert_eq!(format_pairing_code(999999, width).as_str(), "9 9 9  9 9 9");

        // Test with values having exactly 6 digits
        assert_eq!(format_pairing_code(100000, width).as_str(), "1 0 0  0 0 0");

        // Verify behavior with sequential values around boundaries
        assert_eq!(format_pairing_code(9999, width).as_str(), "0 0 9  9 9 9");
        assert_eq!(format_pairing_code(10000, width).as_str(), "0 1 0  0 0 0");
        assert_eq!(format_pairing_code(99999, width).as_str(), "0 9 9  9 9 9");

        // Test different even width (width=4, middle after position 1)
        let width = 4;
        assert_eq!(format_pairing_code(1, width).as_str(), "0 0  0 1");
        assert_eq!(format_pairing_code(12, width).as_str(), "0 0  1 2");
        assert_eq!(format_pairing_code(123, width).as_str(), "0 1  2 3");
        assert_eq!(format_pairing_code(1234, width).as_str(), "1 2  3 4");
    }

    #[test]
    fn test_plural_form() {
        use super::plural_form;
        // malformed templete, returns empty string
        assert_eq!(plural_form("day", 1).as_str(), "day");
        // simple singular/plural
        assert_eq!(plural_form("day|days", 1).as_str(), "day");
        assert_eq!(plural_form("day|days", 3).as_str(), "days");
        // Czech-style singular/few/many
        assert_eq!(plural_form("den|dny|dní", 1).as_str(), "den");
        assert_eq!(plural_form("den|dny|dní", 3).as_str(), "dny");
        assert_eq!(plural_form("den|dny|dní", 5).as_str(), "dní");
    }
}
