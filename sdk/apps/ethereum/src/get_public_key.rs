use crate::proto::{
    common::HdNodeType,
    ethereum::{EthereumGetPublicKey, EthereumPublicKey},
};
use crate::strutil::hex_encode;
use alloc::string::ToString;
use trezor_app_sdk::{Error, Result, crypto, log, ui, util::HdNodeData};

const VERSION: u32 = 0x0488B21E;

pub fn get_public_key(msg: EthereumGetPublicKey) -> Result<EthereumPublicKey> {
    let long_string: &str = "asdfghjklqwertyuiopzxcvbnmASDFGHJKLQWERTYUIOPZXCVBNM0123456789\
    asdfghjklqwertyuiopzxcvbnmASDFGHJKLQWERTYUIOPZXCVBNM0123456789\
    asdfghjklqwertyuiopzxcvbnmASDFGHJKLQWERTYUIOPZXCVBNM0123456789\
    asdfghjklqwertyuiopzxcvbnmASDFGHJKLQWERTYUIOPZXCVBNM0123456789\
    asdfghjklqwertyuiopzxcvbnmASDFGHJKLQWERTYUIOPZXCVBNM0123456789\
    asdfghjklqwertyuiopzxcvbnmASDFGHJKLQWERTYUIOPZXCVBNM0123456789";
    log::info!(
        "string chars: {}, string bytes: {}",
        long_string.chars().count(),
        long_string.len()
    );

    ui::confirm_long_value("title", long_string)?;

    let mut public_key = EthereumPublicKey::default();

    let xpub = crypto::get_xpub(&msg.address_n)?;
    public_key.xpub = xpub.as_str().to_string();

    let node_ll =
        HdNodeData::deserialize_public(xpub.as_str(), VERSION).map_err(|_| Error::DataError)?;

    let mut node = HdNodeType::default();
    node.depth = node_ll.depth;
    node.fingerprint = node_ll.fingerprint;
    node.child_num = node_ll.child_num;
    node.chain_code = node_ll.chain_code.to_vec();
    node.public_key = node_ll.public_key.to_vec();

    if matches!(msg.show_display, Some(true)) {
        let xpub = hex_encode(&node.public_key);
        ui::show_public_key(xpub.as_str())?;
    }

    public_key.node = node;

    Ok(public_key)
}
