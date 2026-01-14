use crate::proto::ethereum::{EthereumGetPublicKey, EthereumPublicKey};
use trezor_app_sdk::Result;

pub fn get_public_key(_msg: EthereumGetPublicKey) -> Result<EthereumPublicKey> {
    Ok(EthereumPublicKey::default())
}
