extern crate alloc;

use alloc::string::String;
use alloc::vec::Vec;

use trezor_app_sdk::{
    ui, {Error, Result},
};

use crate::{
    bitcoin,
    proto::{
        bitcoin::{GetPublicKey, PublicKey},
        common::HdNodeType,
        ethereum::{EthereumGetPublicKey, EthereumPublicKey},
    },
};

/// Ethereum uses Bitcoin xpub format
pub fn get_public_key(msg: EthereumGetPublicKey) -> Result<EthereumPublicKey> {
    // Delegate to Bitcoin get_public_key with same address path
    let btc_msg = GetPublicKey {
        address_n: msg.address_n.clone(),
        coin_name: Some(String::from("Bitcoin")),
        ..Default::default()
    };

    let resp = bitcoin::get_public_key::get_public_key(btc_msg, None, None)?;

    // Show hex-encoded public key if requested
    if msg.show_display.unwrap_or(false) {
        let pubkey_hex = hex_encode(&resp.node.public_key);
        ui::show_public_key(&pubkey_hex)?;
    }

    Ok(EthereumPublicKey {
        node: resp.node,
        xpub: resp.xpub,
    })
}

fn hex_encode(bytes: &[u8]) -> String {
    use core::fmt::Write;
    let mut s = String::new();
    for &b in bytes {
        write!(&mut s, "{:02x}", b).unwrap();
    }
    s
}
