use crate::{helpers::write_compact_size, proto::common::PaymentRequest};
#[cfg(not(test))]
use alloc::{string::ToString, vec::Vec};
use primitive_types::U256;
#[cfg(test)]
use std::vec::Vec;
use trezor_app_sdk::{Error, Result, crypto, info};

const SLIP44_ID_UNDEFINED: u32 = 0xFFFF_FFFF;

const MEMO_TYPE_TEXT: u32 = 1;
const MEMO_TYPE_REFUND: u32 = 2;
const MEMO_TYPE_COIN_PURCHASE: u32 = 3;
const MEMO_TYPE_TEXT_DETAILS: u32 = 4;

pub fn parse_amount(amount: &[u8]) -> Result<U256> {
    if amount.len() != PaymentRequestVerifier::AMOUNT_SIZE_BYTES {
        // TODO: proper error type: DataError("Amount must be exactly AMOUNT_SIZE_BYTES bytes long.")
        return Err(Error::DataError);
    }

    let amount = U256::from_little_endian(&amount);
    Ok(amount)
}

pub fn sanitize_payment_request(payment_request: &PaymentRequest) -> Result<()> {
    for memo in &payment_request.memos {
        let memo_types = [
            memo.text_memo.is_some(),
            memo.text_details_memo.is_some(),
            memo.refund_memo.is_some(),
            memo.coin_purchase_memo.is_some(),
        ];

        info!("memo types {:?}", memo_types);

        if memo_types
            .iter()
            .map(|present| u8::from(*present))
            .sum::<u8>()
            != 1
        {
            // TODO: proper error type: DataError("Exactly one memo type must be specified in each PaymentRequestMemo.")
            return Err(Error::DataError);
        }
    }
    Ok(())
}

pub fn is_coin_swap(payment_request: &PaymentRequest) -> bool {
    let has_coin_purchase = payment_request
        .memos
        .iter()
        .any(|memo| memo.coin_purchase_memo.is_some());
    info!("has coin purchase memo: {}", has_coin_purchase);
    let has_refund = payment_request
        .memos
        .iter()
        .any(|memo| memo.refund_memo.is_some());
    info!("has refund memo: {}", has_refund);

    has_coin_purchase && has_refund
}

// TODO: differentiate debug and release config
pub fn verify_payment_request_is_supported(payment_request: &PaymentRequest) -> Result<()> {
    // if payment_request.memos.is_empty() {
    //     // TODO: proper error type: DataError("Payment request must contain at least one memo.")
    //     info!("payment request must contain at least one memo");
    //     return Err(Error::DataError);
    // }

    // if !is_coin_swap(payment_request) {
    //     // TODO: proper error type: DataError("Only coin swap payment requests are supported.")
    //     info!("only coin swap payment requests are supported");
    //     return Err(Error::DataError);
    // }

    Ok(())
}

const PUBLIC_KEY: [u8; 33] = [
    0x02, 0xaa, 0x9b, 0x94, 0xb3, 0x06, 0xf1, 0xb5, 0x0c, 0x19, 0xb4, 0xb9, 0x53, 0xb6, 0xac, 0xdf,
    0x2d, 0x3a, 0xc0, 0x9e, 0xca, 0x5e, 0x53, 0x44, 0xa2, 0xbb, 0x2f, 0xbf, 0x19, 0x49, 0x5d, 0x55,
    0x0c,
];

// nist256p1 public key of m/0h for "all all ... all" seed.
// Corresponding private key: b"\x05\x62\x35\xb0\x47\x6f\x05\x7f\x27\x65\x21\x97\x24\xf7\xf1\x80\x7d\x58\x80\x2b\x55\x0e\xd5\xbf\x6f\x73\x05\x0a\xf5\x45\x63\x00"
// keeping it here for reference in case tests need to be updated!
const DEBUG_PUBLIC_KEY: [u8; 33] = [
    0x03, 0xd9, 0xd9, 0x3f, 0x89, 0xc6, 0x96, 0x3b, 0x94, 0xbb, 0xd7, 0xa5, 0x11, 0x88, 0x28, 0xe4,
    0x4c, 0x1c, 0x39, 0x59, 0x15, 0xac, 0xe8, 0x48, 0x88, 0x71, 0x7f, 0x56, 0x8c, 0xb0, 0x19, 0x74,
    0xc3,
];

pub struct PaymentRequestVerifier {
    amount: U256,
    expected_amount: Option<U256>,
    h_outputs: crypto::Sha256,
    h_pr: crypto::Sha256,
    signature: Vec<u8>,
}

impl PaymentRequestVerifier {
    const AMOUNT_SIZE_BYTES: usize = 32;
    pub fn new(payment_request: &PaymentRequest, slip44_id: u32) -> Result<Self> {
        info!("sanitizing payment request");
        sanitize_payment_request(&payment_request)?;
        info!("verifying payment request is supported");

        verify_payment_request_is_supported(&payment_request)?;

        let h_outputs = crypto::Sha256::new(None);
        let mut h_pr = crypto::Sha256::new(None);
        let amount = U256::from(0);

        let expected_amount = if let Some(amount) = payment_request.amount.as_deref() {
            info!("parsing expected amount from payment request");
            Some(parse_amount(&amount)?)
        } else {
            None
        };

        let signature = &payment_request.signature;
        let nonce = payment_request.nonce.as_deref().unwrap_or(&[]);

        if !nonce.is_empty() {
            if !crypto::verify_nonce_cache(nonce)? {
                // TODO: proper error type: DataError("Invalid nonce in payment request.")
                info!("invalid nonce in payment request");
                return Err(Error::DataError);
            }
        } else {
            if !payment_request.memos.is_empty() {
                // TODO: proper error type: DataError("Missing nonce in payment request.")
                info!("missing nonce in payment request");
                return Err(Error::DataError);
            }
        };

        h_pr.update(b"SL\x00\x24");

        let prefix = write_compact_size(nonce.len() as _);
        h_pr.update(&prefix);
        h_pr.update(nonce);

        let name_bytes = &payment_request.recipient_name.as_bytes();
        let prefix = write_compact_size(name_bytes.len() as _);
        h_pr.update(&prefix);
        h_pr.update(name_bytes);

        let memos_count_bytes = write_compact_size(payment_request.memos.len() as _);
        h_pr.update(&memos_count_bytes);

        info!("processing memos in payment request");

        for memo in &payment_request.memos {
            if let Some(text_memo) = &memo.text_memo {
                h_pr.update(&u32::from(MEMO_TYPE_TEXT).to_le_bytes());
                let text = &text_memo.text.as_bytes();
                let text_prefix = write_compact_size(text.len() as _);
                h_pr.update(&text_prefix);
                h_pr.update(text);
            } else if let Some(text_details_memo) = &memo.text_details_memo {
                h_pr.update(&u32::from(MEMO_TYPE_TEXT_DETAILS).to_le_bytes());

                let title = &text_details_memo.title.as_bytes();
                let title_prefix = write_compact_size(title.len() as _);
                h_pr.update(&title_prefix);
                h_pr.update(title);

                let text = &text_details_memo.text.as_bytes();
                let text_prefix = write_compact_size(text.len() as _);
                h_pr.update(&text_prefix);
                h_pr.update(text);
            } else if let Some(refund_memo) = &memo.refund_memo {
                if slip44_id == SLIP44_ID_UNDEFINED {
                    // Trezor can not hold coins of type SLIP44_ID_UNDEFINED,
                    // so a refund for a payment request with that coin type makes no sense
                    // TODO: proper error type: DataError("Cannot process refund memo.")
                    info!("cannot process refund memo for undefined coin type");
                    return Err(Error::DataError);
                }
                // Unlike in a coin purchase memo, the coin type is implied by the payment request.
                info!("getting mac");
                let mac: &[u8; 32] = refund_memo.mac.as_slice().try_into().map_err(|_| {
                    // TODO: proper error type
                    Error::DataError
                })?;
                if !crypto::check_address_mac(
                    &refund_memo.address_n,
                    mac,
                    &refund_memo.address,
                    None,
                )? {
                    // TODO: proper error type
                    info!("invalid MAC in refund memo");
                    return Err(Error::DataError);
                }

                h_pr.update(&u32::from(MEMO_TYPE_REFUND).to_le_bytes());
                let address = &refund_memo.address.as_bytes();
                let address_prefix = write_compact_size(address.len() as _);
                h_pr.update(&address_prefix);
                h_pr.update(address);
            } else if let Some(coin_purchase_memo) = &memo.coin_purchase_memo {
                let mac: &[u8; 32] =
                    coin_purchase_memo.mac.as_slice().try_into().map_err(|_| {
                        // TODO: proper error type
                        Error::DataError
                    })?;
                if !crypto::check_address_mac(
                    &coin_purchase_memo.address_n,
                    mac,
                    &coin_purchase_memo.address,
                    None,
                )? {
                    // TODO: proper error type
                    info!("invalid MAC in coin purchase memo");
                    return Err(Error::DataError);
                }
                h_pr.update(&u32::from(MEMO_TYPE_COIN_PURCHASE).to_le_bytes());
                h_pr.update(&u32::from(coin_purchase_memo.coin_type).to_le_bytes());

                let amount = &coin_purchase_memo.amount.as_bytes();
                let amount_prefix = write_compact_size(amount.len() as _);
                h_pr.update(&amount_prefix);
                h_pr.update(amount);

                let address = &coin_purchase_memo.address.as_bytes();
                let address_prefix = write_compact_size(address.len() as _);
                h_pr.update(&address_prefix);
                h_pr.update(address);
            } else {
                // TODO: proper error type: DataError("Unrecognized memo type in payment request.")
                return Err(Error::DataError);
            }
        }
        info!("last hash update");
        h_pr.update(&u32::from(slip44_id).to_le_bytes());

        Ok(PaymentRequestVerifier {
            amount: 0.into(),
            expected_amount,
            h_outputs,
            h_pr,
            signature: signature.to_vec(),
        })
    }

    pub fn verify(&mut self) -> Result<()> {
        if let Some(expected_amount) = self.expected_amount {
            if self.amount != expected_amount {
                // TODO: proper error type: DataError("Invalid amount in payment request.")
                info!(
                    "not similar amount in payment request {}, expected {}",
                    self.amount.to_string().as_str(),
                    expected_amount.to_string().as_str()
                );
                return Err(Error::DataError);
            }
        }

        info!("finalizing hash of outputs and verifying signature in payment request");

        let hash_outputs = self.h_outputs.digest();
        self.h_pr.update(&hash_outputs);

        info!("nist");
        // TODO: differentiate debug and release config
        if !crypto::nist256p1_verify(&DEBUG_PUBLIC_KEY, &self.signature, &self.h_pr.digest()) {
            // TODO: proper error type: raise DataError("Invalid signature in payment request.")
            info!("invalid signature in payment request");
            return Err(Error::DataError);
        }

        info!("payment request verified successfully");

        Ok(())
    }

    pub fn add_output(&mut self, amount: U256, address: &str, change: Option<bool>) -> Result<()> {
        let change = change.unwrap_or(false);
        let encoded_amount = amount.to_little_endian();

        assert!(encoded_amount.len() == Self::AMOUNT_SIZE_BYTES);

        self.h_outputs.update(&encoded_amount);

        let address_bytes = address.as_bytes();
        let address_prefix = write_compact_size(address_bytes.len() as _);
        self.h_outputs.update(&address_prefix);
        self.h_outputs.update(address_bytes);

        if !change {
            self.amount += amount;
        }
        Ok(())
    }
}
