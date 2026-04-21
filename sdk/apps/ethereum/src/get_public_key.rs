use crate::{
    proto::{
        common::{HdNodeType, button_request::ButtonRequestType},
        ethereum::{GetPublicKey, PublicKey},
    },
    strutil::hex_encode,
};
#[cfg(not(test))]
use alloc::string::ToString;
#[cfg(test)]
use std::string::ToString;
use trezor_app_sdk::{Error, Result, crypto, ui, util::HdNodeData};

const VERSION: u32 = 0x0488B21E;

pub fn get_public_key(msg: GetPublicKey) -> Result<PublicKey> {
    let mut public_key = PublicKey::default();

    let xpub = crypto::get_xpub(&msg.address_n)?;
    public_key.xpub = xpub.as_str().to_string();

    let node_ll = HdNodeData::deserialize_public(xpub.as_str(), VERSION)
        .map_err(|_| Error::DataError("Failed to deserialize public key"))?;

    let mut node = HdNodeType::default();
    node.depth = node_ll.depth;
    node.fingerprint = node_ll.fingerprint;
    node.child_num = node_ll.child_num;
    node.chain_code = node_ll.chain_code.to_vec();
    node.public_key = node_ll.public_key.to_vec();

    if matches!(msg.show_display, Some(true)) {
        let xpub = hex_encode(&node.public_key);
        ui::show_public_key(
            xpub.as_str(),
            tr!("address__public_key"),
            None,
            None,
            None,
            "show_pubkey",
            ButtonRequestType::ButtonRequestOther.into(),
        )?;

        ui::show_success(
            tr!("words__title_done"),
            tr!("address__public_key_confirmed"),
            tr!("instructions__continue_in_app"),
            Some(3200),
            None,
            ButtonRequestType::ButtonRequestOther.into(),
        )?;
    }

    public_key.node = node;

    Ok(public_key)
}
