use crate::{
    ProstCodec,
    alloc_types::{String, ToString},
    consts::{SLIP44_ID, TX_TYPE},
    helpers::{address_from_public_key, sha256},
    layout::{
        confirm_tx_final, require_confirm_memo, require_confirm_payment_request,
        require_confirm_tx_source,
    },
    operations::{Operation, process_operation},
    payment_request::{PaymentRequestVerifier, parse_amount},
    proto::{
        common::button_request::ButtonRequestType,
        messages::MessageType,
        stellar::{Asset, SignTx, SignedTx, TxExt, TxExtRequest, TxOpRequest, sign_tx::MemoType},
    },
    tokens::StellarToken,
    writers::{
        Writer, write_bool, write_bytes_fixed, write_pubkey, write_string, write_uint32,
        write_uint64,
    },
};
use prost::Message;
use trezor_app_sdk::crypto::HashingAlgorithm;
use trezor_app_sdk::{Error, Result, ResultExt, WireEncode, crypto, ui, wire_request_raw};

/// Requests the next operation of the transaction from the host.
fn request_operation() -> Result<Operation> {
    let req_bytes = ProstCodec::encode(&TxOpRequest {});
    let (id, data) = wire_request_raw(&req_bytes, MessageType::TxOpRequest as u16).c()?;
    let message_type = MessageType::try_from(id as i32).map_err(|_| Error::InvalidMessage)?;
    Operation::decode(message_type, &data)
}

/// Requests the transaction extension of a Soroban transaction.
fn request_tx_ext() -> Result<TxExt> {
    let req_bytes = ProstCodec::encode(&TxExtRequest {});
    let (id, data) = wire_request_raw(&req_bytes, MessageType::TxExtRequest as u16).c()?;
    if id as i32 != MessageType::TxExt as i32 {
        return Err(Error::InvalidMessage);
    }
    TxExt::decode(data.as_slice()).map_err(|_| Error::InvalidMessage)
}

pub fn sign_tx(msg: SignTx) -> Result<SignedTx> {
    let pubkey = crypto::get_public_key(&msg.address_n, false).c()?;
    let num_operations = msg.num_operations;

    if num_operations == 0 {
        return Err(Error::DataError(
            "Stellar: At least one operation is required",
        ));
    }

    // The transaction is hashed as it is serialized.
    let mut w = crypto::get_hasher(HashingAlgorithm::Sha256);

    // ---------------------------------
    // INIT
    // ---------------------------------
    let mut is_sending_from_trezor_account = true;
    let mut current_output_index = 0usize;

    let network_passphrase_hash = sha256(msg.network_passphrase.as_bytes());
    write_bytes_fixed(&mut w, &network_passphrase_hash, 32).c()?;
    write_bytes_fixed(&mut w, &TX_TYPE, 4).c()?;

    let address = address_from_public_key(&pubkey);
    let accounts_match = msg.source_account == address;

    write_pubkey(&mut w, &msg.source_account).c()?;
    write_uint32(&mut w, msg.fee);
    write_uint64(&mut w, msg.sequence_number);

    if !accounts_match {
        is_sending_from_trezor_account = false;
        // If the tx source account does not match the Trezor account, we need to confirm it.
        require_confirm_tx_source(&msg.source_account).c()?;
    }

    // timebounds are sent as uint32s since that's all we can display, but they must be hashed as 64bit
    write_bool(&mut w, true);
    write_uint64(&mut w, msg.timebounds_start as u64);
    write_uint64(&mut w, msg.timebounds_end as u64);

    let memo_type = MemoType::try_from(msg.memo_type)
        .map_err(|_| Error::DataError("Stellar invalid memo type"))?;
    write_uint32(&mut w, memo_type as u32);
    let memo_confirm_text = match memo_type {
        // nothing is serialized
        MemoType::None => String::new(),
        MemoType::Text => {
            // Text: 4 bytes (size) + up to 28 bytes
            let memo_text = msg
                .memo_text
                .as_deref()
                .ok_or(Error::DataError("Stellar: Missing memo text"))?;
            let written = write_string(&mut w, memo_text.as_bytes());
            if written > 28 {
                return Err(Error::DataError(
                    "Stellar: max length of a memo text is 28 bytes",
                ));
            }
            memo_text.to_string()
        }
        MemoType::Id => {
            // ID: 64 bit unsigned integer
            let memo_id = msg
                .memo_id
                .ok_or(Error::DataError("Stellar: Missing memo id"))?;
            write_uint64(&mut w, memo_id);
            memo_id.to_string()
        }
        MemoType::Hash | MemoType::Return => {
            // Hash/Return: 32 byte hash
            let memo_hash = msg
                .memo_hash
                .as_deref()
                .ok_or(Error::DataError("Stellar: Missing memo hash"))?;
            write_bytes_fixed(&mut w, memo_hash, 32).c()?;
            crate::strutil::hex_encode(memo_hash)
                .map_err(|_| Error::DataError("Stellar: invalid memo hash"))?
        }
    };

    let mut verifier = msg
        .payment_req
        .as_ref()
        .map(|payment_req| PaymentRequestVerifier::new(payment_req, SLIP44_ID))
        .transpose()
        .c()?;

    // ---------------------------------
    // OPERATION
    // ---------------------------------

    // these two are used in case of payment requests, where we allow only one output,
    // hence we have a single output address and asset
    let mut output: Option<(String, Asset)> = None;
    let mut has_soroban_op = false;

    write_uint32(&mut w, num_operations);
    for i in 0..num_operations {
        let op = request_operation().c()?;

        if matches!(op, Operation::InvokeHostFunction(_)) {
            // A Soroban operation must be the only operation in the transaction.
            if num_operations != 1 {
                return Err(Error::DataError(
                    "Stellar: a Soroban operation must be the only operation",
                ));
            }
            if memo_type != MemoType::None {
                return Err(Error::DataError(
                    "Stellar: a Soroban operation cannot be used with a memo",
                ));
            }
            has_soroban_op = true;
        } else if i == 0 {
            // Soroban transactions do not support memos
            require_confirm_memo(memo_type, &memo_confirm_text).c()?;
        }

        process_operation(
            &mut w,
            &op,
            current_output_index,
            verifier.as_mut(),
            &msg.source_account,
            &network_passphrase_hash,
        )
        .c()?;

        if msg.payment_req.is_some() {
            if current_output_index != 0 {
                return Err(Error::DataError(
                    "Multiple operations not supported for payment requests",
                ));
            }
            if output.is_some() {
                return Err(Error::DataError(
                    "Multiple operations not supported for payment requests",
                ));
            }
        }

        if let Some(source_account) = op.source_account()
            && source_account != address
        {
            // if the operation source account does not match the Trezor account
            is_sending_from_trezor_account = false;
        }

        if op.is_output() {
            current_output_index += 1;
            if let Operation::Payment(payment) = &op {
                output = Some((payment.destination_account.clone(), payment.asset.clone()));
            }
        }
    }

    // ---------------------------------
    // FINAL
    // ---------------------------------
    // Transaction extension (ext union)
    if has_soroban_op {
        // For Soroban transactions, request TxExt with soroban_data
        let tx_ext = request_tx_ext().c()?;
        if tx_ext.v != 1 {
            return Err(Error::DataError(
                "Stellar: Soroban transaction requires ext.v = 1",
            ));
        }
        let soroban_data = tx_ext
            .soroban_data
            .as_deref()
            .ok_or(Error::DataError("Stellar: missing soroban_data"))?;
        write_uint32(&mut w, 1); // ext.v = 1
        // Write soroban_data as raw XDR bytes (SorobanTransactionData struct)
        w.write(soroban_data);
    } else {
        // For non-Soroban transactions, ext.v = 0 (empty union).
        // We intentionally do NOT request TxExt here to maintain backward
        // compatibility with existing SDK implementations.
        write_uint32(&mut w, 0);
    }

    if let (Some(verifier), Some(payment_req)) = (verifier.as_mut(), msg.payment_req.as_ref()) {
        verifier.verify().c()?;

        let (output_address, output_asset) = output.as_ref().ok_or(Error::DataError(
            "Stellar: payment request needs a payment operation",
        ))?;

        require_confirm_payment_request(
            output_address,
            payment_req,
            &msg.address_n,
            &StellarToken::from_asset(output_asset).c()?,
            parse_amount(payment_req).c()? as u128,
        )
        .c()?;
    }

    // final confirm
    confirm_tx_final(
        &msg.address_n,
        msg.fee,
        (msg.timebounds_start, msg.timebounds_end),
        is_sending_from_trezor_account,
        &msg.network_passphrase,
    )
    .c()?;

    // sign
    let digest: [u8; 32] = {
        use trezor_app_sdk::crypto::HasherExt as _;
        w.finalize()
            .as_slice()
            .try_into()
            .map_err(|_| Error::DataError("Stellar: invalid digest"))?
    };
    let signature = sign_digest(&msg.address_n, &digest).c()?;

    ui::show_success(ui::ShowSuccess::new(
        tr!("words__title_done"),
        tr!("send__transaction_signed"),
        tr!("instructions__continue_in_app"),
        Some(3200),
        None,
        ButtonRequestType::Success as i32,
    ))
    .c()?;

    // Add the public key for verification that the right account was used for signing
    Ok(SignedTx {
        public_key: pubkey,
        signature: signature.to_vec(),
    })
}

/// Signs `digest` with the Ed25519 key at `address_n`.
///
/// Core returns the 64-byte Ed25519 signature zero-padded to the 65 bytes of
/// the signature type shared with the ECDSA curves.
pub(crate) fn sign_digest(address_n: &[u32], digest: &[u8; 32]) -> Result<[u8; 64]> {
    let signature = crypto::sign_digest(address_n, digest, false).c()?;
    let mut out = [0u8; 64];
    out.copy_from_slice(&signature[..64]);
    Ok(out)
}
