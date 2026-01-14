use trezor_app_sdk::Result;

use crate::proto::ethereum::{EthereumSignTx, EthereumTxRequest};

pub fn sign_tx(_msg: EthereumSignTx) -> Result<EthereumTxRequest> {
    Ok(EthereumTxRequest::default())
}
