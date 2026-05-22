use crate::{
    alloc_types::ToString,
    proto::{
        common::{HdNodeType, button_request::ButtonRequestType},
        ethereum::{GetPublicKey, PublicKey},
    },
    strutil::hex_encode,
};
use trezor_app_sdk::{Error, Result, ResultExt, crypto, ui, util::HdNodeData};

const VERSION: u32 = 0x0488B21E;

pub(crate) fn get_public_key(msg: GetPublicKey) -> Result<PublicKey> {
    let xpub = crypto::get_xpub(&msg.address_n).context("Failed to get xpub")?;
    let node_ll = HdNodeData::deserialize_public(xpub.as_str(), VERSION)
        .map_err(|_| Error::DataError("Failed to deserialize public key"))?;

    let public_key = PublicKey {
        xpub: xpub.as_str().to_string(),
        node: HdNodeType {
            depth: node_ll.depth,
            fingerprint: node_ll.fingerprint,
            child_num: node_ll.child_num,
            chain_code: node_ll.chain_code.to_vec(),
            public_key: node_ll.public_key.to_vec(),
            ..Default::default()
        },
    };

    if matches!(msg.show_display, Some(true)) {
        let xpub = hex_encode(&public_key.node.public_key)
            .map_err(|_| Error::DataError("Failed to hex-encode message"))?;
        ui::error_if_not_confirmed(ui::show_public_key(
            xpub.as_str(),
            tr!("address__public_key"),
            None,
            None,
            None,
            "show_pubkey",
            ButtonRequestType::Other.into(),
        )?)
        .context("Public key was not confirmed")?;

        ui::show_success(
            tr!("words__title_done"),
            tr!("address__public_key_confirmed"),
            tr!("instructions__continue_in_app"),
            Some(3200),
            None,
            ButtonRequestType::Other.into(),
        )?;
    }

    Ok(public_key)
}
