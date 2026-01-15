use crate::proto::ethereum::{EthereumGetPublicKey, EthereumPublicKey};
use trezor_app_sdk::{Result, ui};

pub fn get_public_key(msg: EthereumGetPublicKey) -> Result<EthereumPublicKey> {
    // TODO: Implement Ethereum public key retrieval"
    let public_key = EthereumPublicKey::default();

    // TODO: hexlify(resp.node.public_key).decode()
    if matches!(msg.show_display, Some(true)) {
        ui::show_public_key("aa")?;
    }

    Ok(public_key)
}
