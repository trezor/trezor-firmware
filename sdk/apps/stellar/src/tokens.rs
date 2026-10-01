use crate::{
    alloc_types::String,
    consts::{AMOUNT_DECIMALS, NETWORK_PASSPHRASE_PUBLIC},
    helpers::{contract_address_from_asset, sha256},
    proto::stellar::{Asset, AssetType, InvokeContractArgs},
    strutil::format_amount,
    uformat,
};
use trezor_app_sdk::{Error, Result};

/// Trusted SEP-41 token contracts of the public network that are not Stellar
/// Asset Contracts, and so can never be recognized from a host-supplied asset
/// hint. Keyed by contract address, mapping to `(symbol, decimals)` as the
/// contract itself reports them.
const PUBLIC_TOKENS: [(&str, &str, u32); 4] = [
    // Solv Protocol assets: https://solv.finance/.well-known/stellar.toml
    (
        "CBIJBDNZNF4X35BJ4FFZWCDBSCKOP5NB4PLG4SNENRMLAPYG4P5FM6VN",
        "SolvBTC",
        8,
    ),
    (
        "CAUP7NFABXE5TJRL3FKTPMWRLC7IAXYDCTHQRFSCLR5TMGKHOOQO772J",
        "xSolvBTC",
        8,
    ),
    // Centrifuge assets: https://centrifuge.io/.well-known/stellar.toml
    (
        "CBI7UCH5KGSVQRO5H4SUCZUTZABCITZLRHQQZTWL2TK4RZ72TAR6IHRV",
        "deJTRSY",
        18,
    ),
    (
        "CC64WBDGS6QQP22QTTIACYIXT3WF7BBQEYOQPLTP7GTKYY7PZ74QYGSL",
        "deJAAA",
        18,
    ),
];

/// Identity of the token an amount is denominated in.
///
/// Only a token backed by a classic asset has an issuer; one that exists
/// purely as a SEP-41 contract does not. The contract being invoked is not
/// part of the identity -- it is a property of the invocation and is passed
/// alongside.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct StellarToken {
    pub symbol: String,
    pub decimals: u32,
    pub issuer: Option<String>,
}

impl StellarToken {
    /// XLM, the native asset.
    pub fn native() -> Self {
        Self {
            symbol: String::from("XLM"),
            decimals: AMOUNT_DECIMALS,
            issuer: None,
        }
    }

    /// Describes a classic asset.
    pub fn from_asset(asset: &Asset) -> Result<Self> {
        if asset.r#type == AssetType::Native as i32 {
            // A native asset has neither a code nor an issuer, and
            // `write_asset` leaves both out of the SAC address preimage. They
            // must be ignored here as well, or a host could relabel XLM as an
            // asset of its choice.
            return Ok(Self::native());
        }
        match (&asset.code, &asset.issuer) {
            (Some(code), Some(issuer)) => Ok(Self {
                symbol: code.clone(),
                decimals: AMOUNT_DECIMALS,
                issuer: Some(issuer.clone()),
            }),
            _ => Err(Error::DataError("Stellar: invalid asset definition")),
        }
    }

    /// Formats an amount with this token's precision and symbol.
    pub fn format(&self, amount: u128) -> String {
        uformat!(
            "{} {}",
            format_amount(amount, self.decimals as usize).as_str(),
            self.symbol.as_str()
        )
    }
}

/// Resolves token metadata for the dedicated SEP-41 UI.
///
/// A contract is recognized in two ways. The host may identify a Stellar Asset
/// Contract by supplying its underlying asset; the hint is used only when its
/// derived SAC address matches the invoked contract, so it cannot mislead the
/// user. Otherwise the contract may be one of the tokens hard-coded in the
/// firmware, which are vetted in advance and need no host cooperation at all.
///
/// A SAC match is cryptographically proven, so it takes precedence. Anything
/// left unrecognized goes to the generic contract UI.
pub fn resolve_sep41_token(
    args: &InvokeContractArgs,
    network_id: &[u8; 32],
) -> Option<StellarToken> {
    if let Some(asset) = &args.asset_hint
        && let Ok(sac) = contract_address_from_asset(network_id, asset)
        && sac == args.contract_address
        && let Ok(token) = StellarToken::from_asset(asset)
    {
        return Some(token);
    }

    if *network_id == sha256(NETWORK_PASSPHRASE_PUBLIC.as_bytes()) {
        for (contract, symbol, decimals) in PUBLIC_TOKENS {
            if contract == args.contract_address {
                return Some(StellarToken {
                    symbol: String::from(symbol),
                    decimals,
                    issuer: None,
                });
            }
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn native_token_formats_xlm() {
        assert_eq!(StellarToken::native().format(25_000_000), "2.5 XLM");
    }

    #[test]
    fn native_asset_ignores_code_and_issuer() {
        let asset = Asset {
            r#type: AssetType::Native as i32,
            code: Some(String::from("USD")),
            issuer: Some(String::from("GABC")),
        };
        assert_eq!(
            StellarToken::from_asset(&asset).unwrap(),
            StellarToken::native()
        );
    }

    #[test]
    fn non_native_asset_requires_code_and_issuer() {
        let asset = Asset {
            r#type: AssetType::Alphanum4 as i32,
            code: Some(String::from("USD")),
            issuer: None,
        };
        assert!(StellarToken::from_asset(&asset).is_err());
    }
}
