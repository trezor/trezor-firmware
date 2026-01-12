extern crate alloc;

use alloc::string::String;
use alloc::vec::Vec;

use trezor_app_sdk::Result;

use crate::proto::{
    bitcoin::{GetPublicKey, InputScriptType, PublicKey},
    common::{HdNodeType, MessageType},
};

#[derive(Debug)]
pub enum Error {
    ForbiddenKeyPath,
    InvalidCombination,
}

impl core::fmt::Display for Error {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        match self {
            Error::ForbiddenKeyPath => write!(f, "Forbidden key path"),
            Error::InvalidCombination => write!(f, "Invalid combination of coin and script_type"),
        }
    }
}

/// Simplified get_public_key for Bitcoin/Ethereum use case.
/// Removed: SLIP25 auth, segwit variants, taproot, descriptors, UI warnings.
pub fn get_public_key(
    msg: GetPublicKey,
    _auth_msg: Option<MessageType>,
    keychain: Option<Keychain>,
) -> Result<PublicKey> {
    let coin_name = msg.coin_name.unwrap_or_else(|| String::from("Bitcoin"));
    let script_type = msg
        .script_type
        .unwrap_or(InputScriptType::Spendaddress.into());
    let address_n = msg.address_n;

    // TODO: Replace with real coininfo lookup
    let curve_name = msg
        .ecdsa_curve_name
        .unwrap_or_else(|| String::from("secp256k1"));
    let xpub_magic = 0x0488b21e; // Bitcoin mainnet xpub

    // Get or create keychain
    let mut kc = if let Some(k) = keychain {
        k
    } else {
        get_keychain(&curve_name)?
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

    let root_fingerprint = kc.root_fingerprint();

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

// ===== Placeholder types/functions - replace with your real implementations =====

pub struct Keychain {
    // ... fields from your keychain implementation
}

impl Keychain {
    pub fn derive(&mut self, path: &[u32]) -> Result<Node> {
        // TODO: implement using your keychain logic
        unimplemented!()
    }

    pub fn root_fingerprint(&mut self) -> u32 {
        // TODO: implement
        0
    }
}

pub struct Node {
    // ... fields from your node implementation
}

impl Node {
    pub fn serialize_public(&self, magic: u32) -> String {
        // TODO: implement xpub serialization
        String::from("xpub...")
    }

    pub fn public_key(&self) -> Vec<u8> {
        // TODO: implement
        Vec::new()
    }

    pub fn depth(&self) -> u32 {
        // TODO: implement
        0
    }

    pub fn child_num(&self) -> u32 {
        // TODO: implement
        0
    }

    pub fn fingerprint(&self) -> u32 {
        // TODO: implement
        0
    }

    pub fn chain_code(&self) -> Vec<u8> {
        // TODO: implement
        Vec::new()
    }
}

fn get_keychain(curve: &str) -> Result<Keychain> {
    // TODO: implement seed retrieval and keychain creation
    unimplemented!()
}
