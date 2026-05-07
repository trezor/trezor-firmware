use crate::{
    helpers::get_progress_indicator,
    layout::{require_confirm_claim, require_confirm_stake, require_confirm_unstake},
    paths::Bip32Path,
    proto::{definitions::NetworkInfo, ethereum::SignTx},
    sc_constants::{SC_ARGUMENT_BYTES, SC_FUNC_SIG_BYTES},
};
use primitive_types::U256;
use trezor_app_sdk::{Error, Result, ui::Property, unwrap};

const SC_FUNC_SIG_STAKE: [u8; 4] = [0x3a, 0x29, 0xdb, 0xae];
const SC_FUNC_SIG_UNSTAKE: [u8; 4] = [0x76, 0xec, 0x87, 0x1c];
const SC_FUNC_SIG_CLAIM: [u8; 4] = [0x33, 0x98, 0x6f, 0xfa];

#[cfg(not(test))]
use alloc::boxed::Box;
#[cfg(test)]
use std::boxed::Box;

// addresses for pool (stake/unstake) and accounting (claim) operations
const ADDRESSES_POOL: [[u8; 20]; 2] = [
    [
        0xAF, 0xA8, 0x48, 0x35, 0x71, 0x54, 0xA6, 0xA6, 0x24, 0x68, 0x6B, 0x34, 0x83, 0x03, 0xEF,
        0x9A, 0x13, 0xF6, 0x32, 0x64,
    ], // Hoodi testnet
    [
        0xD5, 0x23, 0x79, 0x4C, 0x87, 0x9D, 0x9E, 0xC0, 0x28, 0x96, 0x0A, 0x23, 0x1F, 0x86, 0x67,
        0x58, 0xE4, 0x05, 0xBE, 0x34,
    ], // mainnet
];

const ADDRESSES_ACCOUNTING: [[u8; 20]; 2] = [
    [
        0x62, 0x40, 0x87, 0xDD, 0x19, 0x04, 0xAB, 0x12, 0x2A, 0x32, 0x87, 0x8C, 0xE9, 0xE9, 0x33,
        0xC7, 0x07, 0x1F, 0x53, 0xB9,
    ], // Hoodi testnet
    [
        0x7A, 0x7F, 0x0B, 0x3C, 0x23, 0xC2, 0x3A, 0x31, 0xCF, 0xCB, 0x0C, 0x44, 0x70, 0x9B, 0xE7,
        0x0D, 0x4D, 0x54, 0x5C, 0x6E,
    ], // mainnet
];

pub(crate) fn get_approver<'a>(
    msg: &'a SignTx,
    dp: &'a Bip32Path,
    network: &'a NetworkInfo,
    address_bytes: &'a [u8],
    maximum_fee: &'a str,
    fee_items: &'a [Property<'a>],
) -> Result<(
    Option<Box<dyn Fn(&[u8]) -> Result<()> + 'a>>,
    Option<Box<dyn FnOnce() -> Result<()> + 'a>>,
)> {
    let data_length = unwrap!(msg.data_length);
    let data_initial_chunk = unwrap!(msg.data_initial_chunk.as_deref());
    let value = unwrap!(msg.value.as_deref());

    if data_length > data_initial_chunk.len() as u32 {
        return Ok((None, None));
    }

    if data_initial_chunk.len() < SC_FUNC_SIG_BYTES {
        return Ok((None, None));
    }

    let (func_sig, data) = data_initial_chunk.split_at(SC_FUNC_SIG_BYTES);

    if ADDRESSES_POOL
        .iter()
        .any(|addr| addr.as_slice() == address_bytes)
    {
        if func_sig == &SC_FUNC_SIG_STAKE {
            return Ok((
                None,
                Some(Box::new(move || {
                    handle_staking_tx_stake(
                        data,
                        &dp,
                        value,
                        network,
                        address_bytes,
                        maximum_fee,
                        fee_items,
                        msg.chunkify,
                    )
                })),
            ));
        } else if func_sig == &SC_FUNC_SIG_UNSTAKE {
            return Ok((
                None,
                Some(Box::new(move || {
                    handle_staking_tx_unstake(
                        data,
                        &dp,
                        network,
                        address_bytes,
                        maximum_fee,
                        fee_items,
                        msg.chunkify,
                    )
                })),
            ));
        }
    }

    if ADDRESSES_ACCOUNTING
        .iter()
        .any(|addr| addr.as_slice() == address_bytes)
    {
        if func_sig == &SC_FUNC_SIG_CLAIM {
            return Ok((
                None,
                Some(Box::new(move || {
                    handle_staking_tx_claim(
                        data,
                        &dp,
                        address_bytes,
                        maximum_fee,
                        fee_items,
                        network,
                        msg.chunkify,
                    )
                })),
            ));
        }
    }

    // data not corresponding to staking transaction
    return Ok((None, None));
}

fn handle_staking_tx_stake<'a>(
    data: &'a [u8],
    dp: &'a Bip32Path,
    value: &'a [u8],
    network: &'a NetworkInfo,
    address_bytes: &'a [u8],
    maximum_fee: &'a str,
    fee_items: &'a [Property<'a>],
    chunkify: Option<bool>,
) -> Result<()> {
    // stake args:
    // - arg0: uint64, source (1 for Trezor)

    // skip arg0
    if data.len() != SC_ARGUMENT_BYTES {
        return Err(Error::DataError("Invalid staking transaction call"));
    }

    assert!(value.len() <= 32);
    let value = U256::from_big_endian(value);

    require_confirm_stake(
        address_bytes,
        value,
        dp,
        maximum_fee,
        fee_items,
        network,
        chunkify.unwrap_or_default(),
    )?;

    Ok(())
}

fn handle_staking_tx_unstake<'a>(
    data: &'a [u8],
    dp: &'a Bip32Path,
    network: &'a NetworkInfo,
    address_bytes: &'a [u8],
    maximum_fee: &'a str,
    fee_items: &'a [Property<'a>],
    chunkify: Option<bool>,
) -> Result<()> {
    // unstake args:
    // - arg0: uint256, value
    // - arg1: uint16, isAllowedInterchange (bool)
    // - arg2: uint64, source (1 for Trezor)

    if data.len() != 3 * SC_ARGUMENT_BYTES {
        return Err(Error::DataError("Invalid staking transaction call"));
    }

    // parse arg0: uint256, value (only lower 16 bytes fit in u128)
    let (arg0, _rest) = data.split_at(SC_ARGUMENT_BYTES);
    // skip arg1 and arg2

    let value = U256::from_big_endian(arg0);

    // skip arg1 and arg2

    require_confirm_unstake(
        address_bytes,
        value,
        dp,
        maximum_fee,
        fee_items,
        network,
        chunkify.unwrap_or_default(),
    )?;

    Ok(())
}

fn handle_staking_tx_claim<'a>(
    data: &'a [u8],
    dp: &'a Bip32Path,
    staking_address: &'a [u8],
    maximum_fee: &'a str,
    fee_items: &'a [Property<'a>],
    network: &'a NetworkInfo,
    chunkify: Option<bool>,
) -> Result<()> {
    // claim has no args
    if data.len() != 0 {
        return Err(Error::DataError("Invalid staking transaction call"));
    }

    require_confirm_claim(
        staking_address,
        dp,
        maximum_fee,
        fee_items,
        network,
        chunkify.unwrap_or_default(),
    )?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::strutil::hex_decode;

    // Verify constants match the hex strings they replaced
    #[test]
    fn test_sc_func_sig_constants() {
        assert_eq!(
            SC_FUNC_SIG_STAKE,
            hex_decode("3a29dbae").unwrap().as_slice()
        );
        assert_eq!(
            SC_FUNC_SIG_UNSTAKE,
            hex_decode("76ec871c").unwrap().as_slice()
        );
        assert_eq!(
            SC_FUNC_SIG_CLAIM,
            hex_decode("33986ffa").unwrap().as_slice()
        );
    }

    #[test]
    fn test_everstake_address_constants() {
        assert_eq!(
            &ADDRESSES_POOL[0][..],
            hex_decode("AFA848357154a6a624686b348303EF9a13F63264")
                .unwrap()
                .as_slice()
        );
        assert_eq!(
            &ADDRESSES_POOL[1][..],
            hex_decode("D523794C879D9eC028960a231F866758e405bE34")
                .unwrap()
                .as_slice()
        );
        assert_eq!(
            &ADDRESSES_ACCOUNTING[0][..],
            hex_decode("624087DD1904ab122A32878Ce9e933C7071F53B9")
                .unwrap()
                .as_slice()
        );
        assert_eq!(
            &ADDRESSES_ACCOUNTING[1][..],
            hex_decode("7a7f0b3c23C23a31cFcb0c44709be70d4D545c6e")
                .unwrap()
                .as_slice()
        );
    }
}
