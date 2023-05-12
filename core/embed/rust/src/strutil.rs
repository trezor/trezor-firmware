use heapless::String;

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
pub trait StringType: AsRef<str> + From<&'static str> + SkipPrefix {}

impl<T> StringType for T where T: AsRef<str> + From<&'static str> + SkipPrefix {}

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
