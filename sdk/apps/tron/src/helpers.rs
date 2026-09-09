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
