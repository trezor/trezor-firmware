extern crate alloc;

use alloc::string::String;
use alloc::vec::Vec;

use trezor_app_sdk::{
    ui, {Error, Result},
};

use crate::proto::ethereum::{EthereumMessageSignature, EthereumSignMessage};

/// Ethereum uses Bitcoin xpub format
pub fn sign_message(_msg: EthereumSignMessage) -> Result<EthereumMessageSignature> {
    // TODO implement actual signing logic
    Ok(EthereumMessageSignature::default())
}
