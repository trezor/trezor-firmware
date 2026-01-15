use crate::{
    layout::require_confirm_vault_tx,
    paths::Bip32Path,
    proto::{
        definitions::{NetworkInfo, TokenInfo},
        ethereum::SignTx,
    },
    sc_constants::SC_FUNC_SIG_BYTES,
    yielding_vaults::{VaultInfo, lookup_vault, unknown_vault},
};

use primitive_types::U256;
use trezor_app_sdk::{Error, Result, ui::Property, unwrap};

#[cfg(not(test))]
use alloc::boxed::Box;
#[cfg(test)]
use std::boxed::Box;

// https://ethereum.org/developers/docs/standards/tokens/erc-4626
pub(crate) const FUNC_SIG_DEPOSIT: &[u8] = b"\x6e\x55\x3f\x65";
pub(crate) const FUNC_SIG_WITHDRAW: &[u8] = b"\xb4\x60\xaf\x94";
pub(crate) const FUNC_SIG_REDEEM: &[u8] = b"\xba\x08\x76\x52";
pub(crate) const FUNC_SIG_CLAIM: &[u8] = b"\x71\xee\x95\xc0";

pub(crate) fn get_approver<'a>(
    // msg: &'a SignTx,
    data_length: usize,
    dp: &'a Bip32Path,
    to: &'a str,
    value: &'a [u8],
    initial_data: &'a [u8],
    network: &'a NetworkInfo,
    address_bytes: &'a [u8],
    maximum_fee: &'a str,
    fee_items: &'a [Property<'a>],
    sender_bytes: &'a [u8],
) -> Result<(
    Option<Box<dyn Fn(&[u8]) -> Result<()> + 'a>>,
    Option<Box<dyn FnOnce() -> Result<()> + 'a>>,
)> {
    // let data_length = unwrap!(msg.data_length);

    if data_length > initial_data.len() {
        return Ok((None, None));
    }

    if initial_data.len() < SC_FUNC_SIG_BYTES {
        return Ok((None, None));
    }

    let (func_sig, data) = initial_data.split_at(SC_FUNC_SIG_BYTES);

    let vault = lookup_vault(network, address_bytes);

    let mut handler = None;
    if [FUNC_SIG_DEPOSIT, FUNC_SIG_WITHDRAW, FUNC_SIG_REDEEM]
        .iter()
        .any(|sig| func_sig == *sig)
    {
        let token = if func_sig == FUNC_SIG_REDEEM {
            vault.vault_token.clone()
        } else {
            vault.asset_token.clone()
        };
        handler = prepare_vault_tx(
            data,
            value,
            to,
            &dp,
            network,
            maximum_fee,
            fee_items,
            sender_bytes,
            vault,
            token,
            func_sig,
        )?;
    } else if func_sig == FUNC_SIG_CLAIM {
        handler = prepare_claim_rewards(
            data,
            dp,
            to,
            value,
            network,
            maximum_fee,
            fee_items,
            sender_bytes,
        )?;
    }

    // TODO: implement
    if handler.is_some() {
        return Ok((None, handler));
    }
    Ok((None, None))
}

fn prepare_vault_tx<'a>(
    data: &'a [u8],
    // msg: &'a SignTx,
    value: &'a [u8],
    to: &'a str,
    dp: &'a Bip32Path,
    network: &'a NetworkInfo,
    maximum_fee: &'a str,
    fee_items: &'a [Property<'a>],
    sender_bytes: &'a [u8],
    vault: VaultInfo,
    token: TokenInfo,
    func_sig: &'a [u8],
) -> Result<Option<Box<dyn FnOnce() -> Result<()> + 'a>>> {
    // deposit(uint256 assets, address receiver)
    // withdraw(uint256 assets, address receiver, address owner)
    // redeem(uint256 shares, address receiver, address owner)
    let is_deposit = func_sig == FUNC_SIG_DEPOSIT;

    let min_data_len = if is_deposit { 32 * 2 } else { 32 * 3 };

    if data.len() < min_data_len || value.is_empty() {
        return Err(Error::DataError(
            "Invalid data for ERC-4626 vault transaction.",
        ));
    }

    let (amount_bytes, rest) = data.split_at(32);

    let amount = U256::from_big_endian(amount_bytes);
    if amount == U256::zero() {
        return Err(Error::DataError(
            "Invalid data for ERC-4626 vault transaction.",
        ));
    }

    let (receiver_bytes, rest) = rest.split_at(32);

    // TODO: use parse_address instead
    if unwrap!(receiver_bytes.first_chunk::<12>()) != &[0; 12] {
        return Err(Error::DataError(
            "Invalid data for ERC-4626 vault transaction.",
        ));
    }

    let (owner_bytes, rest) = if is_deposit {
        (None, rest)
    } else {
        let (owner_bytes, rest) = rest.split_at(32);
        (Some(owner_bytes), rest)
    };

    if !is_vault_tx_safe(&vault, sender_bytes, receiver_bytes, owner_bytes)? {
        return Ok(None);
    }

    let mut extra_data = None;
    if !rest.is_empty() {
        extra_data = Some(rest);
    }

    Ok(Some(Box::new(move || {
        require_confirm_vault_tx(
            amount,
            &dp,
            maximum_fee,
            fee_items,
            network,
            if vault != unknown_vault() {
                &vault.name
            } else {
                to
            },
            token,
            func_sig,
            extra_data,
        )
    })))
}

fn prepare_claim_rewards<'a>(
    _data: &'a [u8],
    // _msg: &'a SignTx,
    _dp: &'a Bip32Path,
    _to: &'a str,
    _value: &'a [u8],
    _network: &'a NetworkInfo,
    _maximum_fee: &'a str,
    _fee_items: &'a [Property<'a>],
    _sender_bytes: &'a [u8],
) -> Result<Option<Box<dyn FnOnce() -> Result<()> + 'a>>> {
    Ok(None)
}

fn is_vault_tx_safe<'a>(
    vault: &'a VaultInfo,
    sender_bytes: &'a [u8],
    receiver_bytes: &'a [u8],
    owner_bytes: Option<&'a [u8]>,
) -> Result<bool> {
    let mut is_calldata_safe = receiver_bytes == sender_bytes;
    if let Some(owner_bytes) = owner_bytes {
        // Withdraw/redeem transaction
        is_calldata_safe = is_calldata_safe && owner_bytes == sender_bytes;
    }

    if is_calldata_safe {
        Ok(true)
    } else {
        // Hard fail for known (Trezor) vaults, blind sign for unknown vaults
        if vault != &unknown_vault() {
            Err(Error::DataError("Vault tx: Signer receiver mismatch"))
        } else {
            Ok(false)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use trezor_app_sdk::crypto::Keccak256;

    #[test]
    fn test_func_constants() {
        assert_eq!(
            FUNC_SIG_DEPOSIT,
            &Keccak256::new(Some(b"deposit(uint256,address)")).digest()[..4]
        );
        assert_eq!(
            FUNC_SIG_WITHDRAW,
            &Keccak256::new(Some(b"withdraw(uint256,address,address)")).digest()[..4]
        );
        assert_eq!(
            FUNC_SIG_REDEEM,
            &Keccak256::new(Some(b"redeem(uint256,address,address)")).digest()[..4]
        );
        assert_eq!(
            FUNC_SIG_CLAIM,
            &Keccak256::new(Some(b"claim(address[],address[],uint256[],bytes32[][])")).digest()
                [..4]
        );
    }
}
