extern crate alloc;

use alloc::string::String;
use trezor_app_sdk::Result;

use crate::{
    common::{
        keychain::{Keychain},
        paths,
    },
    proto::{
        bitcoin::{GetPublicKey, InputScriptType, PublicKey},
        common::{HdNodeType, MessageType},
    },
};

/// Simplified get_public_key for Bitcoin/Ethereum use case.
/// Removed: SLIP25 auth, segwit variants, taproot, descriptors, UI warnings.
pub fn get_public_key(
    msg: GetPublicKey,
    auth_msg: Option<MessageType>,
    keychain: Option<Keychain>,
) -> Result<PublicKey> {
    let coin_name = msg.coin_name.unwrap_or_else(|| String::from("Bitcoin"));
    let script_type = msg
        .script_type
        .unwrap_or(InputScriptType::Spendaddress.into());

    // TODO: Replace with real coininfo lookup
    // let coin = get_coin_info(&coin_name)?;

    // TODO: Replace with real coininfo lookup
    let curve_name = msg
        .ecdsa_curve_name
        .unwrap_or_else(|| String::from("secp256k1"));

    let address_n = msg.address_n;
    let ignore_xpub_magic = msg.ignore_xpub_magic;

    // TODO
    // let xpub_magic = coin.xpub_magic;
    let xpub_magic = 0x0488b21e; // Bitcoin mainnet xpub

    if address_n.len() > 1 && address_n[1] == paths::SLIP25_PURPOSE as u32 {
        // UnlockPath is required to access SLIP25 paths.
        if !matches!(auth_msg, Some(MessageType::UnlockPath)) {
            // TODO: raise ForbiddenKeyPath()
            return Err(trezor_app_sdk::Error::InvalidArgument);
        }
    }

    // Get or create keychain
    let mut kc = if let Some(k) = keychain {
        k
    } else {
        // TODO: get keychain with real implementation
        return Err(trezor_app_sdk::Error::InvalidArgument);
    };

    // Derive node from path
    let node = kc.derive(&address_n)?;

    // Serialize xpub (only SPENDADDRESS branch for simplicity)
    let spendaddress: i32 = InputScriptType::Spendaddress.into();
    let spendmultisig: i32 = InputScriptType::Spendmultisig.into();

    let node_xpub = if script_type == spendaddress || script_type == spendmultisig {
        node.serialize_public(xpub_magic)
    } else {
        return Err(trezor_app_sdk::Error::InvalidArgument);
    };

    let pubkey = node.public_key();
    let node_type = HdNodeType {
        depth: node.depth(),
        child_num: node.child_num(),
        fingerprint: node.fingerprint(),
        chain_code: node.chain_code(),
        public_key: pubkey,
        private_key: None,
    };

    let root_fingerprint = kc.root_fingerprint(&from_seed);

    // Show xpub on display if requested
    if msg.show_display.unwrap_or(false) {
        trezor_app_sdk::ui::show_public_key(&node_xpub)?;
    }

    Ok(PublicKey {
        node: node_type,
        xpub: node_xpub,
        root_fingerprint: Some(root_fingerprint),
        descriptor: None, // Not needed for Ethereum
    })
}
