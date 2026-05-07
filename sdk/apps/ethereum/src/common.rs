use crate::{
    clear_signing,
    clear_signing_definitions::SC_FUNC_APPROVE_REVOKE_AMOUNT,
    definitions::Definitions,
    helpers::{address_from_bytes, format_ethereum_amount},
    layout::{
        require_confirm_address, require_confirm_approve, require_confirm_payment_request,
        require_confirm_tx,
    },
    paths::Bip32Path,
    payment_request::PaymentRequestVerifier,
    proto::{
        common::button_request::ButtonRequestType,
        ethereum::{SignTx, TxAck, TxRequest},
        messages::MessageType,
    },
    rlp, staking, uformat, wire_request, yielding,
};
#[cfg(not(test))]
use alloc::{
    boxed::Box,
    string::{String, ToString},
    vec::Vec,
};
use primitive_types::U256;
#[cfg(test)]
use std::{
    boxed::Box,
    string::{String, ToString},
    vec::Vec,
};
use trezor_app_sdk::{
    Error, Result, crypto::{self, Hasher},
    ui::{self, Property},
    unwrap,
};

pub const COIN: &str = "ETH";

// EIP-7702
pub const EIP_7702_TX_TYPE: u32 = 4;

// EIP-7702
const ADDR_EIP7702_UNISWAP: [u8; 20] = [
    0x00, 0x00, 0x00, 0x00, 0x9b, 0x1d, 0x0a, 0xf2, 0x0d, 0x8c, 0x6d, 0x0a, 0x44, 0xe1, 0x62, 0xd1,
    0x1f, 0x9b, 0x8f, 0x00,
];
const ADDR_EIP7702_ALCHEMY: [u8; 20] = [
    0x69, 0x00, 0x77, 0x02, 0x76, 0x41, 0x79, 0xf1, 0x4f, 0x51, 0xcd, 0xce, 0x75, 0x2f, 0x4f, 0x77,
    0x5d, 0x74, 0xe1, 0x39,
];
const ADDR_EIP7702_AMBIRE: [u8; 20] = [
    0x5a, 0x7f, 0xc1, 0x13, 0x97, 0xe9, 0xa8, 0xad, 0x41, 0xbf, 0x10, 0xbf, 0x13, 0xf2, 0x2b, 0x0a,
    0x63, 0xf9, 0x6f, 0x6d,
];
const ADDR_EIP7702_METAMASK: [u8; 20] = [
    0x63, 0xc0, 0xc1, 0x9a, 0x28, 0x2a, 0x1b, 0x52, 0xb0, 0x7d, 0xd5, 0xa6, 0x5b, 0x58, 0x94, 0x8a,
    0x07, 0xda, 0xe3, 0x2b,
];
const ADDR_EIP7702_EF_AA: [u8; 20] = [
    0x4c, 0xd2, 0x41, 0xe8, 0xd1, 0x51, 0x0e, 0x30, 0xb2, 0x07, 0x63, 0x97, 0xaf, 0xc7, 0x50, 0x8a,
    0xe5, 0x9c, 0x66, 0xc9,
];
const ADDR_EIP7702_LUGANODES: [u8; 20] = [
    0x17, 0xc1, 0x1f, 0xdd, 0xad, 0xac, 0x2b, 0x34, 0x1f, 0x24, 0x55, 0xaf, 0xe9, 0x88, 0xfe, 0xc4,
    0xc3, 0xba, 0x26, 0xe3,
];

const EIP7702_KNOWN_ADDRESSES: [([u8; 20], &str); 6] = [
    (ADDR_EIP7702_UNISWAP, "Uniswap"),
    (ADDR_EIP7702_ALCHEMY, "alchemyplatform"),
    (ADDR_EIP7702_AMBIRE, "AmbireTech"),
    (ADDR_EIP7702_METAMASK, "MetaMask"),
    (ADDR_EIP7702_EF_AA, "Ethereum Foundation AA team"),
    (ADDR_EIP7702_LUGANODES, "Luganodes"),
];

pub fn get_eip_7702_known_address(addr: &[u8]) -> Option<&'static str> {
    EIP7702_KNOWN_ADDRESSES
        .iter()
        .find(|(a, _)| a.as_slice() == addr)
        .map(|(_, name)| *name)
}

pub(crate) fn decode_message(message: &[u8]) -> String {
    match core::str::from_utf8(message) {
        Ok(s) => s.to_string(),
        Err(_) => {
            use crate::strutil::hex_encode;
            uformat!("hex({})", hex_encode(message).as_str())
        }
    }
}

/// Request at most `MAX_DATA_STORED` which we keep locally
pub(crate) fn request_initial_data(
    msg: &SignTx,
    hasher: &mut crypto::Keccak256,
) -> Result<Vec<u8>> {
    let data_length = unwrap!(msg.data_length) as usize;
    let data_initial_chunk = unwrap!(msg.data_initial_chunk.as_deref());

    assert!(data_length >= data_initial_chunk.len());

    // pre-allocate memory
    let mut initial_data = Vec::with_capacity(data_length);

    initial_data.extend_from_slice(data_initial_chunk);
    rlp::write_header(
        hasher,
        data_length as u32,
        rlp::STRING_HEADER_BYTE,
        Some(data_initial_chunk),
    );
    hasher.update(data_initial_chunk);
    let mut data_left = data_length - data_initial_chunk.len();

    while data_left > 0 {
        let resp = send_request_chunk(data_left as u32)?;
        let chunk = resp.data_chunk.as_ref();
        initial_data.extend_from_slice(chunk);
        data_left -= chunk.len();
        hasher.update(chunk);
    }

    Ok(initial_data)
}

pub(crate) fn send_request_chunk(data_left: u32) -> Result<TxAck> {
    let mut req = TxRequest::default();
    req.data_length = Some(core::cmp::min(data_left, 1024) as u32);
    let resp: TxAck = wire_request(&req, MessageType::TxRequest)?;

    Ok(resp)
}

pub(crate) fn check_common_fields(
    data_length: u32,
    data_initial_chunk: &[u8],
    to: &str,
    chain_id: u64,
) -> Result<()> {
    if data_length > 0 {
        if data_initial_chunk.is_empty() {
            return Err(Error::DataError(
                "Data length provided, but no initial chunk",
            ));
        }

        // Our encoding only supports transactions up to 2^24 bytes. To
        // prevent exceeding the limit we use a stricter limit on data length.
        if data_length > 16_000_000 {
            return Err(Error::DataError("Data length exceeds limit"));
        }

        if data_initial_chunk.len() > data_length as usize {
            return Err(Error::DataError("Invalid size of initial chunk"));
        }
    }

    if !matches!(to.len(), 0 | 40 | 42) {
        return Err(Error::DataError("Invalid recipient address"));
    }

    if to.is_empty() && data_length == 0 {
        // sending transaction to address 0 (contract creation) without a data field
        return Err(Error::DataError("Contract creation without data"));
    }

    if chain_id == 0 {
        return Err(Error::DataError("Chain ID out of bounds"));
    }

    Ok(())
}

/// Returns data chunk callback and transaction summary layout to be awaited.
/// [None, None] implies clear signing attempted and succeeded.
pub(crate) fn confirm_tx_data<'a>(
    initial_data: &'a [u8],
    msg: &'a SignTx,
    dp: &'a Bip32Path,
    defs: &'a Definitions,
    tx_type: Option<u32>,
    address_bytes: &'a [u8],
    maximum_fee: &'a str,
    fee_items: &'a [Property<'a>],
    payment_request_verifier: Option<PaymentRequestVerifier>,
    sender_bytes: &'a [u8],
) -> Result<(
    Option<Box<dyn Fn(&[u8]) -> Result<()> + 'a>>,
    Option<Box<dyn FnOnce() -> Result<()> + 'a>>,
)> {
    let value_bytes = unwrap!(msg.value.as_deref());
    let data_length = unwrap!(msg.data_length);

    let staking_approver = staking::get_approver(
        msg,
        &dp,
        defs.network(),
        address_bytes,
        maximum_fee,
        fee_items,
    )?;

    if staking_approver.1.is_some() {
        if payment_request_verifier.is_some() {
            return Err(Error::DataError("Payment Requests don't support staking"));
        }
        return Ok(staking_approver);
    }

    let yielding_approver = yielding::get_approver(
        &msg,
        &dp,
        initial_data,
        defs.network(),
        address_bytes,
        maximum_fee,
        fee_items,
        sender_bytes,
    )?;

    if yielding_approver.1.is_some() {
        if payment_request_verifier.is_some() {
            return Err(Error::DataError("Payment Requests don't support yielding"));
        }
        return Ok(yielding_approver);
    }

    if matches!(tx_type, Some(EIP_7702_TX_TYPE)) {
        // we have already made sure that the address is a known address
        // as part of the initial validation

        ui::error_if_not_confirmed(ui::confirm_value(
            tr!("ethereum__eip_7702_title"),
            unwrap!(get_eip_7702_known_address(&address_bytes)),
            Some(tr!("ethereum__eip_7702")),
            Some("confirm_provider"),
            ButtonRequestType::ButtonRequestOther.into(),
            true,
            None,
            None,
            false,
            false,
            false,
            false,
            false,
            false,
            None,
        )?)?;
    }

    let value = U256::from_big_endian(value_bytes);

    let mut clear_signed = false;
    if (initial_data.len() as u32) < data_length {
        // Don't even attempt to clear sign if we have a calldata larger than `MAX_DATA_STORED`.
        // this is because clear signing doesn't currently support fetching additional data,
        // which is because if it did, we would not be able to fall back to blind signing anymore.
        clear_signed = false;
    } else {
        if clear_signing::try_parse(
            initial_data,
            address_bytes,
            msg,
            defs,
            maximum_fee,
            fee_items,
            payment_request_verifier.as_ref(),
        )
        .is_err()
        {
            clear_signed = false;
        }
    }

    let recipient_str = if address_bytes.is_empty() {
        None
    } else {
        Some(address_from_bytes(address_bytes, Some(defs.network())))
    };

    if let Some(mut payment_request_verifier) = payment_request_verifier {
        assert!(data_length == 0);

        //  If a payment_request_verifier is provided, then msg.payment_req must have been set.
        assert!(msg.payment_req.is_some());
        assert!(recipient_str.is_some());

        payment_request_verifier.add_output(value, recipient_str.as_deref().unwrap_or(""), None)?;
        payment_request_verifier.verify()?;
        // TODO: implement
        Ok((
            None,
            Some(Box::new(move || {
                require_confirm_payment_request(
                    unwrap!(recipient_str.as_deref()),
                    unwrap!(msg.payment_req.as_ref()),
                    &dp,
                    maximum_fee,
                    fee_items,
                    msg.chain_id,
                    defs.network(),
                    None,
                    None,
                )
            })),
        ))
    } else if !clear_signed {
        // TODO: implement
        // let confirm_data_chunk: Option<_> = if data_length > 0 {
        //     // get_data_confirmer(data_length)
        //     None
        // } else {
        //     // get_progress_indicator(data_length)
        //     None
        // };
        // what we want to confirm here is the ETH amount being sent on-chain
        let token = None;

        let is_send = data_length == 0 && tx_type != Some(EIP_7702_TX_TYPE);

        // TODO: implement
        Ok((
            None,
            Some(Box::new(move || {
                require_confirm_tx(
                    recipient_str.as_deref(),
                    &format_ethereum_amount(value, token, defs.network(), false),
                    address_bytes,
                    &dp,
                    maximum_fee,
                    fee_items,
                    token,
                    is_send,
                    msg.chunkify.unwrap_or_default(),
                )
            })),
        ))
    } else {
        Ok((None, None))
    }
}



pub(crate) fn confirm_data_and_summary<'a>(
    confirm_data_chunk: Option<Box<dyn Fn(&[u8]) -> Result<()> + 'a>>,
    confirm_summary: Option<Box<dyn FnOnce() -> Result<()> + 'a>>,
    initial_data: &[u8],
    data_length: usize,
    hasher: &mut crypto::Keccak256,
) -> Result<()> {
    // `confirm_data_chunk` and `confirm_summary` can be `None`
    // if we clear signed so there is nothing more to confirm

    if let Some(confirm_data_chunk) = confirm_data_chunk {
        confirm_data_chunk(initial_data)?;

        let mut data_left = data_length - initial_data.len();
        while data_left > 0 {
            let resp = send_request_chunk(data_left as u32)?;
            let chunk = resp.data_chunk.as_ref();
            confirm_data_chunk(chunk)?;
            data_left -= chunk.len();
            hasher.update(chunk);
        }
    }

    if let Some(confirm_summary) = confirm_summary {
        // blind signer's summary
        confirm_summary()?;
    }
    Ok(())
}

// fn handle_known_contract_calls(
//     data_initial_chunk: &[u8],
//     data_length: u32,
//     to: &str,
//     value_bytes: &[u8],
//     definitions: &Definitions,
//     address_bytes: &[u8],
// ) -> Result<(
//     Option<TokenInfo>,
//     Option<Vec<u8>>,
//     Option<[u8; SC_FUNC_SIG_BYTES]>,
//     Vec<u8>,
//     Option<U256>,
// )> {
//     let mut token = None;
//     let mut token_address = None;
//     let mut recipient = Vec::from(address_bytes);

//     // TODO: better implement parsing int value from bytes
//     assert!(value_bytes.len() <= 32);
//     let mut value = Some(U256::from_big_endian(value_bytes));

//     if data_initial_chunk.len() < SC_FUNC_SIG_BYTES {
//         return Ok((token, token_address, None, recipient, value));
//     }

//     let (sig, rest) = unwrap!(data_initial_chunk.split_first_chunk::<SC_FUNC_SIG_BYTES>());

//     let mut func_sig = Some(*sig);

//     if matches!(to.len(), 40 | 42)
//         && value_bytes.len() == 0
//         && data_length == 68
//         && data_initial_chunk.len() == 68
//         && (matches!(func_sig.as_deref(), Some(sig) if sig == &SC_FUNC_SIG_TRANSFER)
//             || matches!( func_sig.as_deref(), Some(sig) if sig == &SC_FUNC_SIG_APPROVE))
//     {
//         // The two functions happen to have the exact same parameters, so we treat them together.
//         // This will need to be made into a more generic solution eventually.
//         // arg0: address, Address, 20 bytes (left padded with zeroes)
//         // arg1: value, uint256, 32 bytes

//         if rest.len() < SC_ARGUMENT_BYTES * 2 {
//             return Ok((token, token_address, None, recipient, value));
//         }

//         let (arg0, rest) = unwrap!(rest.split_first_chunk::<SC_ARGUMENT_BYTES>());

//         let pad_len = SC_ARGUMENT_BYTES - SC_ARGUMENT_ADDRESS_BYTES;
//         assert!(arg0[..pad_len].iter().all(|&byte| byte == 0));
//         recipient = Vec::from(&arg0[pad_len..]);

//         let (arg1, rest) = unwrap!(rest.split_first_chunk::<SC_ARGUMENT_BYTES>());

//         if matches!(func_sig.as_deref(), Some(sig) if sig == &SC_FUNC_SIG_APPROVE)
//             && arg1.iter().all(|&byte| byte == 255)
//         {
//             // "Unlimited" approval (all bits set) is a special case
//             // which we encode as value=None internally.
//             value = None;
//         } else {
//             value = Some(U256::from_big_endian(arg1));
//         }

//         token = Some(definitions.get_token(address_bytes));
//         token_address = Some(Vec::from(address_bytes));
//     } else {
//         // If the function was known but something else (data length) was unexpected,
//         // pretend we did not recognize the function so we fall back to blind signing.
//         // See the approve_avantis test case and ERC-8021.

//         func_sig = None;
//     };

//     Ok((token, token_address, func_sig, recipient, value))
// }

#[cfg(test)]
mod tests {
    use super::*;
    use crate::strutil::hex_decode;

    #[test]
    fn test_eip7702_known_address_constants() {
        assert_eq!(
            &ADDR_EIP7702_UNISWAP[..],
            hex_decode("000000009B1D0aF20D8C6d0A44e162d11F9b8f00")
                .unwrap()
                .as_slice()
        );
        assert_eq!(
            &ADDR_EIP7702_ALCHEMY[..],
            hex_decode("69007702764179f14F51cdce752f4f775d74E139")
                .unwrap()
                .as_slice()
        );
        assert_eq!(
            &ADDR_EIP7702_AMBIRE[..],
            hex_decode("5A7FC11397E9a8AD41BF10bf13F22B0a63f96f6d")
                .unwrap()
                .as_slice()
        );
        assert_eq!(
            &ADDR_EIP7702_METAMASK[..],
            hex_decode("63c0c19a282a1b52b07dd5a65b58948a07dae32b")
                .unwrap()
                .as_slice()
        );
        assert_eq!(
            &ADDR_EIP7702_EF_AA[..],
            hex_decode("4Cd241E8d1510e30b2076397afc7508Ae59C66c9")
                .unwrap()
                .as_slice()
        );
        assert_eq!(
            &ADDR_EIP7702_LUGANODES[..],
            hex_decode("17c11FDdADac2b341F2455aFe988fec4c3ba26e3")
                .unwrap()
                .as_slice()
        );
    }
}
