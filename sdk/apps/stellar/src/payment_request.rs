//! SLIP-0024 payment request verification, ported from Core's
//! `apps/common/payment_request.py` (with 8-byte amounts, as used by Stellar).

use crate::{alloc_types::Vec, proto::common::PaymentRequest};
use trezor_app_sdk::{
    Error, Result, ResultExt,
    crypto::{self, BoxedHasher, EcCurve, HasherExt, HashingAlgorithm},
};

const SLIP44_ID_UNDEFINED: u32 = 0xFFFF_FFFF;

const MEMO_TYPE_TEXT: u32 = 1;
const MEMO_TYPE_REFUND: u32 = 2;
const MEMO_TYPE_COIN_PURCHASE: u32 = 3;
const MEMO_TYPE_TEXT_DETAILS: u32 = 4;

const AMOUNT_SIZE_BYTES: usize = 8;

/// nist256p1 public key of the trusted payment request signer.
const PUBLIC_KEY: [u8; 33] = [
    0x02, 0xaa, 0x9b, 0x94, 0xb3, 0x06, 0xf1, 0xb5, 0x0c, 0x19, 0xb4, 0xb9, 0x53, 0xb6, 0xac, 0xdf,
    0x2d, 0x3a, 0xc0, 0x9e, 0xca, 0x5e, 0x53, 0x44, 0xa2, 0xbb, 0x2f, 0xbf, 0x19, 0x49, 0x5d, 0x55,
    0x0c,
];

// nist256p1 public key of m/0h for "all all ... all" seed.
// Corresponding private key: b"\x05\x62\x35\xb0\x47\x6f\x05\x7f\x27\x65\x21\x97\x24\xf7\xf1\x80\x7d\x58\x80\x2b\x55\x0e\xd5\xbf\x6f\x73\x05\x0a\xf5\x45\x63\x00"
// keeping it here for reference in case tests need to be updated!
#[cfg(feature = "dev_keys")]
const DEBUG_PUBLIC_KEY: [u8; 33] = [
    0x03, 0xd9, 0xd9, 0x3f, 0x89, 0xc6, 0x96, 0x3b, 0x94, 0xbb, 0xd7, 0xa5, 0x11, 0x88, 0x28, 0xe4,
    0x4c, 0x1c, 0x39, 0x59, 0x15, 0xac, 0xe8, 0x48, 0x88, 0x71, 0x7f, 0x56, 0x8c, 0xb0, 0x19, 0x74,
    0xc3,
];

/// Compact size encoding of a length, as used by SLIP-0024.
fn compact_size(n: u32) -> Vec<u8> {
    let mut out = Vec::with_capacity(5);
    if n < 253 {
        out.push(n as u8);
    } else if n < 0x1_0000 {
        out.push(253);
        out.extend_from_slice(&(n as u16).to_le_bytes());
    } else {
        out.push(254);
        out.extend_from_slice(&n.to_le_bytes());
    }
    out
}

fn write_bytes_prefixed(hasher: &mut BoxedHasher, data: &[u8]) {
    hasher.update(&compact_size(data.len() as u32));
    hasher.update(data);
}

/// Total amount requested by a verified payment request.
pub fn parse_amount(payment_request: &PaymentRequest) -> Result<u64> {
    let amount = payment_request
        .amount
        .as_deref()
        .ok_or(Error::DataError("Payment request has no amount"))?;
    parse_amount_bytes(amount)
}

fn parse_amount_bytes(amount: &[u8]) -> Result<u64> {
    let bytes: [u8; AMOUNT_SIZE_BYTES] = amount
        .try_into()
        .map_err(|_| Error::DataError("amount must be exactly 8 bytes"))?;
    Ok(u64::from_le_bytes(bytes))
}

fn sanitize_payment_request(payment_request: &PaymentRequest) -> Result<()> {
    for memo in &payment_request.memos {
        let present = [
            memo.text_memo.is_some(),
            memo.text_details_memo.is_some(),
            memo.refund_memo.is_some(),
            memo.coin_purchase_memo.is_some(),
        ]
        .into_iter()
        .filter(|present| *present)
        .count();
        if present != 1 {
            return Err(Error::DataError(
                "Exactly one memo type must be specified in each PaymentRequestMemo.",
            ));
        }
    }
    Ok(())
}

#[cfg(not(feature = "dev_keys"))]
fn is_coin_swap(payment_request: &PaymentRequest) -> bool {
    let has_coin_purchase = payment_request
        .memos
        .iter()
        .any(|m| m.coin_purchase_memo.is_some());
    let has_refund = payment_request
        .memos
        .iter()
        .any(|m| m.refund_memo.is_some());
    has_coin_purchase && has_refund
}

#[cfg(not(feature = "dev_keys"))]
fn is_sell(payment_request: &PaymentRequest) -> bool {
    let has_text = payment_request.memos.iter().any(|m| m.text_memo.is_some());
    let has_refund = payment_request
        .memos
        .iter()
        .any(|m| m.refund_memo.is_some());
    has_text && has_refund
}

fn verify_payment_request_is_supported(_payment_request: &PaymentRequest) -> Result<()> {
    // Development builds accept any payment request, like Core's debug mode.
    #[cfg(not(feature = "dev_keys"))]
    {
        if _payment_request.memos.is_empty() {
            return Err(Error::DataError(
                "Payment request must contain at least one memo.",
            ));
        }
        if !is_sell(_payment_request) && !is_coin_swap(_payment_request) {
            return Err(Error::DataError(
                "Supported payment requests are SELL and SWAP.",
            ));
        }
    }
    Ok(())
}

pub struct PaymentRequestVerifier {
    amount: u64,
    expected_amount: Option<u64>,
    h_outputs: BoxedHasher,
    h_pr: BoxedHasher,
    signature: Vec<u8>,
}

impl PaymentRequestVerifier {
    /// Validates the payment request's memos and starts hashing what its
    /// signature covers. Address MACs are verified by Core.
    pub fn new(payment_request: &PaymentRequest, slip44_id: u32) -> Result<Self> {
        sanitize_payment_request(payment_request).c()?;
        verify_payment_request_is_supported(payment_request).c()?;

        let h_outputs = crypto::get_hasher(HashingAlgorithm::Sha256);
        let mut h_pr = crypto::get_hasher(HashingAlgorithm::Sha256);

        let expected_amount = payment_request
            .amount
            .as_deref()
            .map(parse_amount_bytes)
            .transpose()
            .c()?;

        let nonce = payment_request.nonce.as_deref().unwrap_or(&[]);
        if !nonce.is_empty() {
            if !crypto::verify_nonce_cache(nonce).c()? {
                return Err(Error::DataError("Invalid nonce in payment request."));
            }
        } else if !payment_request.memos.is_empty() {
            return Err(Error::DataError("Missing nonce in payment request."));
        }

        h_pr.update(b"SL\x00\x24");
        write_bytes_prefixed(&mut h_pr, nonce);
        write_bytes_prefixed(&mut h_pr, payment_request.recipient_name.as_bytes());
        h_pr.update(&compact_size(payment_request.memos.len() as u32));

        for memo in &payment_request.memos {
            if let Some(text_memo) = &memo.text_memo {
                h_pr.update(&MEMO_TYPE_TEXT.to_le_bytes());
                write_bytes_prefixed(&mut h_pr, text_memo.text.as_bytes());
            } else if let Some(refund_memo) = &memo.refund_memo {
                if slip44_id == SLIP44_ID_UNDEFINED {
                    // Trezor can not hold coins of type SLIP44_ID_UNDEFINED,
                    // so a refund for a payment request with that coin type
                    // makes no sense
                    return Err(Error::DataError("Cannot process refund memo."));
                }
                // Unlike in a coin purchase memo, the coin type is implied by
                // the payment request.
                check_mac(
                    &refund_memo.address_n,
                    &refund_memo.mac,
                    &refund_memo.address,
                )
                .map_err(|_| Error::DataError("Invalid MAC in refund memo"))?;
                h_pr.update(&MEMO_TYPE_REFUND.to_le_bytes());
                write_bytes_prefixed(&mut h_pr, refund_memo.address.as_bytes());
            } else if let Some(coin_purchase_memo) = &memo.coin_purchase_memo {
                check_mac(
                    &coin_purchase_memo.address_n,
                    &coin_purchase_memo.mac,
                    &coin_purchase_memo.address,
                )
                .map_err(|_| Error::DataError("Invalid MAC in coin purchase memo"))?;
                h_pr.update(&MEMO_TYPE_COIN_PURCHASE.to_le_bytes());
                h_pr.update(&coin_purchase_memo.coin_type.to_le_bytes());
                write_bytes_prefixed(&mut h_pr, coin_purchase_memo.amount.as_bytes());
                write_bytes_prefixed(&mut h_pr, coin_purchase_memo.address.as_bytes());
            } else if let Some(text_details_memo) = &memo.text_details_memo {
                h_pr.update(&MEMO_TYPE_TEXT_DETAILS.to_le_bytes());
                write_bytes_prefixed(&mut h_pr, text_details_memo.title.as_bytes());
                write_bytes_prefixed(&mut h_pr, text_details_memo.text.as_bytes());
            } else {
                return Err(Error::DataError(
                    "Unrecognized memo type in payment request.",
                ));
            }
        }

        h_pr.update(&slip44_id.to_le_bytes());

        Ok(Self {
            amount: 0,
            expected_amount,
            h_outputs,
            h_pr,
            signature: payment_request.signature.clone(),
        })
    }

    /// Checks the requested amount and the trusted party's signature.
    pub fn verify(&mut self) -> Result<()> {
        if let Some(expected_amount) = self.expected_amount
            && self.amount != expected_amount
        {
            return Err(Error::DataError("Invalid amount in payment request."));
        }

        let hash_outputs = self.h_outputs.finalize();
        self.h_pr.update(&hash_outputs);
        let digest = self.h_pr.finalize();

        let mut valid = crypto::ec_verify_recover_digest(
            EcCurve::Nist256p1,
            &PUBLIC_KEY,
            &self.signature,
            &digest,
        )
        .is_ok();

        #[cfg(feature = "dev_keys")]
        if !valid {
            valid = crypto::ec_verify_recover_digest(
                EcCurve::Nist256p1,
                &DEBUG_PUBLIC_KEY,
                &self.signature,
                &digest,
            )
            .is_ok();
        }

        if !valid {
            return Err(Error::DataError("Invalid signature in payment request."));
        }
        Ok(())
    }

    pub fn add_output(&mut self, amount: u64, address: &str) -> Result<()> {
        self.h_outputs.update(&amount.to_le_bytes());
        write_bytes_prefixed(&mut self.h_outputs, address.as_bytes());
        self.amount = self
            .amount
            .checked_add(amount)
            .ok_or(Error::DataError("Payment request amount overflow"))?;
        Ok(())
    }
}

fn check_mac(address_n: &[u32], mac: &[u8], address: &str) -> Result<()> {
    let mac: &[u8; 32] = mac
        .try_into()
        .map_err(|_| Error::DataError("Invalid MAC"))?;
    if crypto::check_address_mac(address_n, mac, address).c()? {
        Ok(())
    } else {
        Err(Error::DataError("Invalid MAC"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn compact_size_encoding() {
        assert_eq!(compact_size(0), [0]);
        assert_eq!(compact_size(252), [252]);
        assert_eq!(compact_size(253), [253, 253, 0]);
        assert_eq!(compact_size(0x1_0000), [254, 0, 0, 1, 0]);
    }

    #[test]
    fn amount_is_eight_little_endian_bytes() {
        assert_eq!(parse_amount_bytes(&[1, 0, 0, 0, 0, 0, 0, 0]).unwrap(), 1);
        assert!(parse_amount_bytes(&[0; 32]).is_err());
    }
}
