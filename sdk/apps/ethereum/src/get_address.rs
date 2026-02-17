use crate::proto::ethereum::{EthereumAddress, EthereumGetAddress};
use trezor_app_sdk::Result;

/// Ethereum uses Bitcoin xpub format
pub fn get_address(_msg: EthereumGetAddress) -> Result<EthereumAddress> {
    // TODO: Implement Ethereum address retrieval
    Ok(EthereumAddress::default())
}
