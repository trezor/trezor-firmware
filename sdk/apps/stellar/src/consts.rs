use crate::proto::messages::MessageType;

pub const COIN: &str = "Stellar";
pub const CURVE: &str = "ed25519";
pub const SLIP44_ID: u32 = 148;

/// `TransactionV0`/`ENVELOPE_TYPE_TX` discriminant that prefixes the signed
/// transaction payload.
pub const TX_TYPE: [u8; 4] = [0x00, 0x00, 0x00, 0x02];

// https://www.stellar.org/developers/guides/concepts/accounts.html#balance
// https://github.com/stellar/go/blob/3d2c1defe73dbfed00146ebe0e8d7e07ce4bb1b6/amount/main.go#L23
pub const AMOUNT_DECIMALS: u32 = 7;

// https://developers.stellar.org/docs/networks
pub const NETWORK_PASSPHRASE_PUBLIC: &str = "Public Global Stellar Network ; September 2015";
pub const NETWORK_PASSPHRASE_TESTNET: &str = "Test SDF Network ; September 2015";
pub const NETWORK_PASSPHRASE_FUTURENET: &str = "Test SDF Future Network ; October 2022";

// https://www.stellar.org/developers/guides/concepts/accounts.html#flags
pub const FLAG_AUTH_REQUIRED: u32 = 1;
pub const FLAG_AUTH_REVOCABLE: u32 = 2;
pub const FLAG_AUTH_IMMUTABLE: u32 = 4;
pub const FLAGS_MAX_SIZE: u32 = 7;

/// The HashIDPreimage variant contract IDs are derived from (CAP-46-02)
/// https://github.com/stellar/stellar-xdr/blob/v28.0/Stellar-ledger-entries.x#L666
pub const ENVELOPE_TYPE_CONTRACT_ID: u32 = 8;

/// SCSymbol is a string with a maximum length of 32
/// https://github.com/stellar/stellar-xdr/blob/v26.0/Stellar-contract.x#L211
pub const SCSYMBOL_MAX_SIZE: usize = 32;

/// Operation type discriminant as used in the XDR, for the operation
/// messages the device accepts (Inflation is not supported, see
/// https://github.com/trezor/trezor-core/issues/202#issuecomment-393342089).
///
/// Source: https://github.com/stellar/go/blob/a1db2a6b1f/xdr/Stellar-transaction.x#L35
pub fn op_code(message: MessageType) -> Option<u32> {
    Some(match message {
        MessageType::CreateAccountOp => 0,
        MessageType::PaymentOp => 1,
        MessageType::PathPaymentStrictReceiveOp => 2,
        MessageType::ManageSellOfferOp => 3,
        MessageType::CreatePassiveSellOfferOp => 4,
        MessageType::SetOptionsOp => 5,
        MessageType::ChangeTrustOp => 6,
        MessageType::AllowTrustOp => 7,
        MessageType::AccountMergeOp => 8,
        MessageType::ManageDataOp => 10,
        MessageType::BumpSequenceOp => 11,
        MessageType::ManageBuyOfferOp => 12,
        MessageType::PathPaymentStrictSendOp => 13,
        MessageType::ClaimClaimableBalanceOp => 15,
        MessageType::InvokeHostFunctionOp => 24,
        _ => return None,
    })
}
