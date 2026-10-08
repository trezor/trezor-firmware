use crate::alloc_types::{String, ToString, Vec};
use core::{convert::Infallible, result::Result};
use ufmt::uWrite;
pub struct StringWriter(String);
impl StringWriter {
    pub fn new() -> Self {
        Self(String::new())
    }
    pub fn finalize(self) -> String {
        self.0
    }
}

impl uWrite for StringWriter {
    type Error = Infallible;
    fn write_str(&mut self, s: &str) -> Result<(), Self::Error> {
        self.0.push_str(s);
        Ok(())
    }
}

// Returns an `alloc::string::String` using `ufmt::uwrite!`
// from https://docs.rs/ufmt/latest/ufmt/
// like `std::format!` it returns a `String` but uses `uwrite!`
// instead of `write!`
#[macro_export]
macro_rules! uformat {
    (len:$len:expr, $($tt:tt)*) => {
        {
            use trezor_app_sdk::unwrap;
            let mut s = heapless::String::<$len>::new();
            unwrap!(ufmt::uwrite!(&mut s, $($tt)*));
            s
        }
    };
    ($($tt:tt)*) => {
        {
            use trezor_app_sdk::unwrap;
            let mut s = $crate::strutil::StringWriter::new();
            unwrap!(ufmt::uwrite!(&mut s, $($tt)*));
            s.finalize()
        }
    };
}

pub fn hex_encode(bytes: &[u8]) -> Result<String, ()> {
    let mut s = StringWriter::new();
    for byte in bytes {
        ufmt::uwrite!(&mut s, "{:02x}", *byte).map_err(|_| ())?;
    }
    Ok(s.finalize())
}

pub fn hex_decode(hex: &str) -> Result<Vec<u8>, ()> {
    if !hex.len().is_multiple_of(2) {
        return Err(());
    }

    let mut bytes = Vec::with_capacity(hex.len() / 2);
    let chars: Vec<char> = hex.chars().collect();

    for i in (0..chars.len()).step_by(2) {
        let high = chars[i].to_digit(16).ok_or(())?;
        let low = chars[i + 1].to_digit(16).ok_or(())?;
        bytes.push(((high << 4) | low) as u8);
    }

    Ok(bytes)
}

pub fn format_plural_english(count: u32, singular: &str) -> String {
    let mut plural = singular.to_string();
    if count != 1 {
        // candy -> candies, but key -> keys
        if singular.ends_with('y')
            && !matches!(
                singular.chars().nth_back(1),
                Some('a' | 'e' | 'i' | 'o' | 'u' | 'y')
            )
        {
            plural.pop(); // remove trailing 'y'
            plural.push_str("ies");
        } else if matches!(singular.chars().last(), Some('h' | 's' | 'x' | 'z')) {
            plural.push_str("es");
        } else {
            plural.push('s');
        }
    }

    uformat!("{} {}", count, plural.as_str())
}

/// Formats a non-negative amount given as decimal digits, like Core's
/// `strings.format_amount`: thousands are grouped with `,` and trailing zeros
/// of the fractional part are dropped.
pub fn format_amount_from_digits(digits: &str, decimals: usize) -> String {
    let mut out = String::with_capacity(digits.len() + digits.len() / 3 + decimals + 3);

    let (int_part, frac_part) = if digits.len() <= decimals {
        ("0", None)
    } else {
        let (i, f) = digits.split_at(digits.len() - decimals);
        (i, Some(f))
    };

    for (i, ch) in int_part.chars().enumerate() {
        if i != 0 && (int_part.len() - i) % 3 == 0 {
            out.push(',');
        }
        out.push(ch);
    }

    if decimals > 0 {
        out.push('.');
        if frac_part.is_none() {
            for _ in 0..decimals - digits.len() {
                out.push('0');
            }
            out.push_str(digits);
        } else if let Some(f) = frac_part {
            out.push_str(f);
        }
        while out.ends_with('0') {
            out.pop();
        }
        if out.ends_with('.') {
            out.pop();
        }
    }

    out
}

pub fn format_amount(amount: u128, decimals: usize) -> String {
    format_amount_from_digits(&amount.to_string(), decimals)
}

/// Human-friendly UTC representation of a unix timestamp, e.g.
/// `2021-03-18 07:17:04`. Returns `None` for timestamps that cannot be
/// represented (the caller then shows the raw number).
pub fn format_timestamp(timestamp: u64) -> Option<String> {
    // Same range Core's `utime.gmtime1970` accepts.
    if timestamp > u32::MAX as u64 {
        return None;
    }
    let days = (timestamp / 86_400) as i64;
    let secs = timestamp % 86_400;

    // Civil-from-days (Howard Hinnant's algorithm).
    let z = days + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z.rem_euclid(146_097);
    let yoe = (doe - doe / 1_460 + doe / 36_524 - doe / 146_096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let day = doy - (153 * mp + 2) / 5 + 1;
    let month = if mp < 10 { mp + 3 } else { mp - 9 };
    let year = yoe + era * 400 + i64::from(month <= 2);

    Some(uformat!(
        "{}-{}{}-{}{} {}{}:{}{}:{}{}",
        year,
        if month < 10 { "0" } else { "" },
        month,
        if day < 10 { "0" } else { "" },
        day,
        if secs / 3_600 < 10 { "0" } else { "" },
        secs / 3_600,
        if secs % 3_600 / 60 < 10 { "0" } else { "" },
        secs % 3_600 / 60,
        if secs % 60 < 10 { "0" } else { "" },
        secs % 60
    ))
}

/// Picks the singular/plural form out of a `singular|plural` translation and
/// prefixes it with `count`.
fn plural(count: u64, forms: &str) -> String {
    let (singular, plural) = forms.split_once('|').unwrap_or((forms, forms));
    uformat!("{} {}", count, if count == 1 { singular } else { plural })
}

/// Human-friendly duration given in seconds, joining all non-zero components
/// (e.g. 61 seconds -> "1 minute 1 second").
pub fn format_duration(seconds: u64) -> String {
    let units = [
        (tr!("plurals__days"), 24 * 60 * 60),
        (tr!("plurals__hours"), 60 * 60),
        (tr!("plurals__minutes"), 60),
        (tr!("plurals__seconds"), 1),
    ];

    let mut components: Vec<String> = Vec::new();
    let mut remainder = seconds;
    for (forms, divisor) in units {
        let count = remainder / divisor;
        remainder %= divisor;
        if count != 0 {
            components.push(plural(count, forms));
        }
    }

    if components.is_empty() {
        // zero duration: use the smallest unit
        return plural(0, tr!("plurals__seconds"));
    }
    components.join(" ")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_format_amount() {
        assert_eq!(format_amount(0, 7), "0");
        assert_eq!(format_amount(1, 7), "0.0000001");
        assert_eq!(format_amount(10_000_000, 7), "1");
        assert_eq!(format_amount(123_456_789_012, 7), "12,345.6789012");
        assert_eq!(format_amount(1_500_000_000, 7), "150");
        assert_eq!(format_amount(5, 0), "5");
    }

    #[test]
    fn test_format_timestamp() {
        assert_eq!(format_timestamp(0).unwrap(), "1970-01-01 00:00:00");
        assert_eq!(format_timestamp(1616051824).unwrap(), "2021-03-18 07:17:04");
        assert!(format_timestamp(u64::MAX).is_none());
    }

    #[test]
    fn test_format_duration() {
        crate::test_init::init_sdk();
        assert_eq!(format_duration(0), "0 seconds");
        assert_eq!(format_duration(1), "1 second");
        assert_eq!(format_duration(61), "1 minute 1 second");
        assert_eq!(format_duration(90_061), "1 day 1 hour 1 minute 1 second");
    }

    #[test]
    fn test_hex_encode_empty() {
        let result = hex_encode(&[]).unwrap();
        assert_eq!(result, "");
    }

    #[test]
    fn test_hex_encode_single_byte() {
        let result = hex_encode(&[0xAB]).unwrap();
        assert_eq!(result, "ab");
    }

    #[test]
    fn test_hex_encode_multiple_bytes() {
        let result = hex_encode(&[0x00, 0xFF, 0xAB, 0xCD]).unwrap();
        assert_eq!(result, "00ffabcd");
    }

    #[test]
    fn test_hex_encode_all_zeros() {
        let result = hex_encode(&[0x00, 0x00, 0x00]).unwrap();
        assert_eq!(result, "000000");
    }

    #[test]
    fn test_hex_decode_empty() {
        let result = hex_decode("");
        assert_eq!(result, Ok(vec![]));
    }

    #[test]
    fn test_hex_decode_single_byte() {
        let result = hex_decode("ab");
        assert_eq!(result, Ok(vec![0xAB]));
    }

    #[test]
    fn test_hex_decode_multiple_bytes() {
        let result = hex_decode("00ffabcd");
        assert_eq!(result, Ok(vec![0x00, 0xFF, 0xAB, 0xCD]));
    }

    #[test]
    fn test_hex_decode_uppercase() {
        let result = hex_decode("ABCD");
        assert_eq!(result, Ok(vec![0xAB, 0xCD]));
    }

    #[test]
    fn test_hex_decode_mixed_case() {
        let result = hex_decode("AaBbCc");
        assert_eq!(result, Ok(vec![0xAA, 0xBB, 0xCC]));
    }

    #[test]
    fn test_hex_decode_invalid_characters() {
        // Test various invalid characters
        assert_eq!(hex_decode("GH"), Err(()));
        assert_eq!(hex_decode("zz"), Err(()));
        assert_eq!(hex_decode("!!"), Err(()));
        assert_eq!(hex_decode("@#"), Err(()));
        assert_eq!(hex_decode("--"), Err(()));
    }

    #[test]
    fn test_hex_decode_with_spaces() {
        assert_eq!(hex_decode("ab cd"), Err(()));
        assert_eq!(hex_decode(" abcd"), Err(()));
        assert_eq!(hex_decode("abcd "), Err(()));
    }

    #[test]
    fn test_hex_decode_with_prefix() {
        // Common prefixes that should fail
        assert_eq!(hex_decode("0xabcd"), Err(()));
        assert_eq!(hex_decode("0X1234"), Err(()));
    }

    #[test]
    fn test_hex_decode_odd_length() {
        assert_eq!(hex_decode("a"), Err(()));
        assert_eq!(hex_decode("abc"), Err(()));
        assert_eq!(hex_decode("abcdf"), Err(()));
    }

    #[test]
    fn test_hex_decode_special_characters() {
        assert_eq!(hex_decode("\n\n"), Err(()));
        assert_eq!(hex_decode("\t\t"), Err(()));
        assert_eq!(hex_decode("ab\ncd"), Err(()));
    }

    #[test]
    fn test_hex_decode_unicode() {
        assert_eq!(hex_decode("äb"), Err(()));
        assert_eq!(hex_decode("αβ"), Err(()));
    }

    #[test]
    fn test_hex_encode_decode_roundtrip() {
        let original = vec![0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0];
        let encoded = hex_encode(&original).unwrap();
        let decoded = hex_decode(&encoded).expect("decode failed");
        assert_eq!(decoded, original);
    }
}
