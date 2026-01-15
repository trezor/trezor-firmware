use crate::{
    proto::definitions::{NetworkInfo, TokenInfo},
    tokens::unknown_token,
};

#[cfg(not(test))]
use alloc::{string::String, vec};
#[cfg(test)]
use std::{string::String, vec};

#[derive(PartialEq)]
pub(crate) struct VaultInfo {
    pub address: Option<[u8; 20]>,
    pub chain_id: Option<u64>,
    pub name: String,
    pub asset_token: TokenInfo,
    pub vault_token: TokenInfo,
}

pub(crate) fn unknown_vault() -> VaultInfo {
    VaultInfo {
        address: None,
        chain_id: None,
        name: "UNKNOWN VAULT".into(),
        asset_token: unknown_token(),
        vault_token: unknown_token(),
    }
}

fn known_vaults() -> [VaultInfo; 3] {
    [
        VaultInfo {
            // 0xa511d618cD0F9d7cAD791009d7c5E3b19c9568da
            address: Some([
                0xa5, 0x11, 0xd6, 0x18, 0xcd, 0x0f, 0x9d, 0x7c, 0xad, 0x79, 0x10, 0x09, 0xd7, 0xc5,
                0xe3, 0xb1, 0x9c, 0x95, 0x68, 0xda,
            ]),
            chain_id: Some(1),
            name: "Test Steakhouse USDC Prime Vault".into(),
            asset_token: TokenInfo {
                symbol: "USDC".into(),
                decimals: 6,
                address: vec![
                    0xa0, 0xb8, 0x69, 0x91, 0xc6, 0x21, 0x8b, 0x36, 0xc1, 0xd1, 0x9d, 0x4a, 0x2e,
                    0x9e, 0xb0, 0xce, 0x36, 0x06, 0xeb, 0x48,
                ],
                chain_id: 1,
                name: "USD Coin".into(),
            },
            vault_token: TokenInfo {
                symbol: "tstSHUSDCp".into(),
                decimals: 18,
                address: vec![
                    0xa5, 0x11, 0xd6, 0x18, 0xcd, 0x0f, 0x9d, 0x7c, 0xad, 0x79, 0x10, 0x09, 0xd7,
                    0xc5, 0xe3, 0xb1, 0x9c, 0x95, 0x68, 0xda,
                ],
                chain_id: 1,
                name: "Test Steakhouse USDC Prime Vault".into(),
            },
        },
        VaultInfo {
            // 0xde6c23E561F3e55846207EC45A91b777e0F7C889
            address: Some([
                0xde, 0x6c, 0x23, 0xe5, 0x61, 0xf3, 0xe5, 0x58, 0x46, 0x20, 0x7e, 0xc4, 0x5a, 0x91,
                0xb7, 0x77, 0xe0, 0xf7, 0xc8, 0x89,
            ]),
            chain_id: Some(1),
            name: "Trezor Steakhouse USDC Prime Vault".into(),
            asset_token: TokenInfo {
                symbol: "USDC".into(),
                decimals: 6,
                address: vec![
                    0xa0, 0xb8, 0x69, 0x91, 0xc6, 0x21, 0x8b, 0x36, 0xc1, 0xd1, 0x9d, 0x4a, 0x2e,
                    0x9e, 0xb0, 0xce, 0x36, 0x06, 0xeb, 0x48,
                ],
                chain_id: 1,
                name: "USD Coin".into(),
            },
            vault_token: TokenInfo {
                symbol: "trSHUSDCp".into(),
                decimals: 18,
                address: vec![
                    0xde, 0x6c, 0x23, 0xe5, 0x61, 0xf3, 0xe5, 0x58, 0x46, 0x20, 0x7e, 0xc4, 0x5a,
                    0x91, 0xb7, 0x77, 0xe0, 0xf7, 0xc8, 0x89,
                ],
                chain_id: 1,
                name: "Trezor Steakhouse USDC Prime Vault".into(),
            },
        },
        VaultInfo {
            // 0xE4DB1c5A1B709CE4d2adA6985D9D506e58F73829
            address: Some([
                0xe4, 0xdb, 0x1c, 0x5a, 0x1b, 0x70, 0x9c, 0xe4, 0xd2, 0xad, 0xa6, 0x98, 0x5d, 0x9d,
                0x50, 0x6e, 0x58, 0xf7, 0x38, 0x29,
            ]),
            chain_id: Some(1),
            name: "Trezor Steakhouse USDT Prime Vault".into(),
            asset_token: TokenInfo {
                symbol: "USDT".into(),
                decimals: 6,
                address: vec![
                    0xda, 0xc1, 0x7f, 0x95, 0x8d, 0x2e, 0xe5, 0x23, 0xa2, 0x20, 0x62, 0x06, 0x99,
                    0x45, 0x97, 0xc1, 0x3d, 0x83, 0x1e, 0xc7,
                ],
                chain_id: 1,
                name: "Tether USD".into(),
            },
            vault_token: TokenInfo {
                symbol: "trSHUSDTp".into(),
                decimals: 18,
                address: vec![
                    0xe4, 0xdb, 0x1c, 0x5a, 0x1b, 0x70, 0x9c, 0xe4, 0xd2, 0xad, 0xa6, 0x98, 0x5d,
                    0x9d, 0x50, 0x6e, 0x58, 0xf7, 0x38, 0x29,
                ],
                chain_id: 1,
                name: "Trezor Steakhouse USDT Prime Vault".into(),
            },
        },
    ]
}

pub(crate) fn get_token_label(token_addr: &[u8], network: &NetworkInfo) -> &'static str {
    // Only known token for now. We can use clear signing here to request token definitions from Connect, once it is done.
    // Would move it to EthereumVaultInfo but there don't seem to be plans to add more tokens for now.
    // https://etherscan.io/token/0x58d97b57bb95320f9a05dc918aef65434969c2b2
    const MORPHO_ADDR: [u8; 20] = [
        0x58, 0xd9, 0x7b, 0x57, 0xbb, 0x95, 0x32, 0x0f, 0x9a, 0x05, 0xdc, 0x91, 0x8a, 0xef, 0x65,
        0x43, 0x49, 0x69, 0xc2, 0xb2,
    ];

    if network.chain_id == 1 && token_addr == MORPHO_ADDR {
        "MORPHO"
    } else {
        "UNKNOWN"
    }
}

pub(crate) fn lookup_vault(network: &NetworkInfo, vault_addr: &[u8]) -> VaultInfo {
    for vault in known_vaults() {
        if let (Some(chain_id), Some(address)) = (vault.chain_id, vault.address) {
            if network.chain_id == chain_id && vault_addr == address {
                return vault;
            }
        }
    }
    unknown_vault()
}
