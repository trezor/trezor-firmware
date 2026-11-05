use crate::{
    alloc_types::{String, ToString},
    uformat,
};

use primitive_types::U256;

pub fn format_trx_amount(amount: u64) -> String {
    // 1 SUN = 0.000001 TRX
    const TRX_AMOUNT_DECIMALS: u32 = 6;

    uformat!(
        "{} TRX",
        format_amount_from_digits(&amount.to_string(), TRX_AMOUNT_DECIMALS as usize).as_str()
    )
}

pub fn format_token_amount(amount: U256, token_decimals: u32, token_symbol: &str) -> String {
    uformat!(
        "{} {}",
        format_amount_from_digits(&amount.to_string(), token_decimals as usize).as_str(),
        token_symbol
    )
}

pub fn format_energy_amount(amount: u64) -> String {
    uformat!(
        "{} SUN",
        format_amount_from_digits(&amount.to_string(), 0).as_str()
    )
}

fn format_amount_from_digits(digits: &str, decimals: usize) -> String {
    let mut out = String::with_capacity(digits.len() + digits.len() / 3 + 3);

    if decimals == 0 {
        push_grouped_digits(&mut out, digits);
        return out;
    }

    if digits.len() <= decimals {
        out.push('0');
        out.push('.');
        for _ in 0..(decimals - digits.len()) {
            out.push('0');
        }
        out.push_str(digits);
    } else {
        let split = digits.len() - decimals;
        let (int_part, frac_part) = digits.split_at(split);
        push_grouped_digits(&mut out, int_part);
        out.push('.');
        out.push_str(frac_part);
    }

    while out.ends_with('0') {
        out.pop();
    }
    if out.ends_with('.') {
        out.pop();
    }

    out
}

fn push_grouped_digits(out: &mut String, digits: &str) {
    for (i, ch) in digits.chars().enumerate() {
        if i != 0 && (digits.len() - i).is_multiple_of(3) {
            out.push(',');
        }
        out.push(ch);
    }
}

/// Formats a block count as a duration (Tron produces one block every 3 seconds), e.g. "3d 2h".
pub fn format_blocks_as_time(blocks: u64) -> String {
    let total_seconds = blocks * 3;

    let days = total_seconds / 86400;
    let hours = (total_seconds % 86400) / 3600;
    let minutes = (total_seconds % 3600) / 60;
    let seconds = total_seconds % 60;

    let mut out = String::new();
    for (value, unit) in [(days, 'd'), (hours, 'h'), (minutes, 'm'), (seconds, 's')] {
        if value != 0 {
            if !out.is_empty() {
                out.push(' ');
            }
            out.push_str(&value.to_string());
            out.push(unit);
        }
    }
    out
}

/// Groups digits from the right in chunks of 3 separated by spaces, e.g. 1234 => "1 234".
pub fn chunkify_number(number: u64) -> String {
    let digits = number.to_string();
    let mut out = String::with_capacity(digits.len() + digits.len() / 3);
    for (i, ch) in digits.chars().enumerate() {
        if i != 0 && (digits.len() - i).is_multiple_of(3) {
            out.push(' ');
        }
        out.push(ch);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_format_blocks_as_time() {
        assert_eq!(format_blocks_as_time(0), "");
        assert_eq!(format_blocks_as_time(1), "3s");
        assert_eq!(format_blocks_as_time(20), "1m");
        assert_eq!(format_blocks_as_time(86400), "3d");
        assert_eq!(format_blocks_as_time(86400 + 1201), "3d 1h 3s");
    }

    #[test]
    fn test_chunkify_number() {
        assert_eq!(chunkify_number(0), "0");
        assert_eq!(chunkify_number(123), "123");
        assert_eq!(chunkify_number(1234), "1 234");
        assert_eq!(chunkify_number(123456), "123 456");
        assert_eq!(chunkify_number(1234567), "1 234 567");
    }
}
