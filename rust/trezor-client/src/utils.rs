use crate::error::{Error, Result};
use bitcoin::{
    address,
    address::Payload,
    bip32,
    blockdata::script::Script,
    hashes::{sha256d, Hash},
    psbt,
    secp256k1::ecdsa::{RecoverableSignature, RecoveryId},
    Address, Network,
};

/// Retrieve an address from the given script.
pub fn address_from_script(script: &Script, network: Network) -> Option<address::Address> {
    let payload = Payload::from_script(script).ok()?;
    Some(Address::new(network, payload))
}

/// Find the (first if multiple) PSBT input that refers to the given txid.
pub fn psbt_find_input(
    psbt: &psbt::PartiallySignedTransaction,
    txid: sha256d::Hash,
) -> Result<&psbt::Input> {
    let inputs = &psbt.unsigned_tx.input;
    let idx = inputs
        .iter()
        .position(|tx| *tx.previous_output.txid.as_raw_hash() == txid)
        .ok_or(Error::TxRequestUnknownTxid(txid))?;
    psbt.inputs.get(idx).ok_or(Error::TxRequestInvalidIndex(idx))
}

/// Get a hash from a reverse byte representation.
pub fn from_rev_bytes(rev_bytes: &[u8]) -> Option<sha256d::Hash> {
    let mut bytes = rev_bytes.to_vec();
    bytes.reverse();
    sha256d::Hash::from_slice(&bytes).ok()
}

/// Get the reverse byte representation of a hash.
pub fn to_rev_bytes(hash: &sha256d::Hash) -> [u8; 32] {
    let mut bytes = hash.to_byte_array();
    bytes.reverse();
    bytes
}

/// Parse a Bitcoin Core-style 65-byte recoverable signature.
pub fn parse_recoverable_signature(
    sig: &[u8],
) -> Result<RecoverableSignature, bitcoin::secp256k1::Error> {
    if sig.len() != 65 {
        return Err(bitcoin::secp256k1::Error::InvalidSignature)
    }

    // Bitcoin Core sets the first byte to `27 + rec + (fCompressed ? 4 : 0)`.
    let rec_id = RecoveryId::from_i32(if sig[0] >= 31 {
        (sig[0] - 31) as i32
    } else {
        (sig[0] - 27) as i32
    })?;

    RecoverableSignature::from_compact(&sig[1..], rec_id)
}

/// Convert a bitcoin network constant to the Trezor-compatible coin_name string.
pub fn coin_name(network: Network) -> Result<String> {
    match network {
        Network::Bitcoin => Ok("Bitcoin".to_owned()),
        Network::Testnet => Ok("Testnet".to_owned()),
        _ => Err(Error::UnsupportedNetwork),
    }
}

/// Convert a BIP-32 derivation path into a `Vec<u32>`.
pub fn convert_path(path: &bip32::DerivationPath) -> Vec<u32> {
    path.into_iter().map(|i| u32::from(*i)).collect()
}
