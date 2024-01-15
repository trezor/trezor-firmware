use super::{handle_interaction, Trezor};
use crate::{
    error::Result,
    protos::{self, ethereum_sign_tx_eip1559::EthereumAccessList, EthereumTxRequest},
    Error,
};

/// Access list item.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AccessListItem {
    /// Accessed address
    pub address: String,
    /// Accessed storage keys
    pub storage_keys: Vec<Vec<u8>>,
}

/// An ECDSA signature.
#[derive(Debug, Clone, PartialEq, Eq, Copy)]
pub struct Signature {
    /// R value
    pub r: [u8; 32],
    /// S Value
    pub s: [u8; 32],
    /// V value in 'Electrum' notation.
    pub v: u64,
}

impl Trezor {
    // ETHEREUM
    pub fn ethereum_get_address(&mut self, path: Vec<u32>) -> Result<String> {
        let mut req = protos::EthereumGetAddress::new();
        req.address_n = path;
        let address = handle_interaction(
            self.call(req, Box::new(|_, m: protos::EthereumAddress| Ok(m.address().into())))?,
        )?;
        Ok(address)
    }

    pub fn ethereum_sign_message(&mut self, message: Vec<u8>, path: Vec<u32>) -> Result<Signature> {
        let mut req = protos::EthereumSignMessage::new();
        req.address_n = path;
        req.set_message(message);
        let signature = handle_interaction(self.call(
            req,
            Box::new(|_, m: protos::EthereumMessageSignature| {
                let signature = m.signature();
                if signature.len() != 65 {
                    return Err(Error::MalformedSignature)
                }
                let r = signature[0..32].try_into().unwrap();
                let s = signature[32..64].try_into().unwrap();
                let v = signature[64] as u64;
                Ok(Signature { r, s, v })
            }),
        )?)?;

        Ok(signature)
    }

    #[allow(clippy::too_many_arguments)]
    pub fn ethereum_sign_tx(
        &mut self,
        path: Vec<u32>,
        nonce: Vec<u8>,
        gas_price: Vec<u8>,
        gas_limit: Vec<u8>,
        to: String,
        value: Vec<u8>,
        data: Vec<u8>,
        chain_id: Option<u64>,
    ) -> Result<Signature> {
        let mut req = protos::EthereumSignTx::new();
        let mut data = data;

        req.address_n = path;
        req.set_nonce(nonce);
        req.set_gas_price(gas_price);
        req.set_gas_limit(gas_limit);
        req.set_value(value);
        if let Some(chain_id) = chain_id {
            req.set_chain_id(chain_id);
        }
        req.set_to(to);

        req.set_data_length(data.len() as u32);
        req.set_data_initial_chunk(data.splice(..std::cmp::min(1024, data.len()), []).collect());

        let mut resp =
            handle_interaction(self.call(req, Box::new(|_, m: protos::EthereumTxRequest| Ok(m)))?)?;

        while resp.data_length() > 0 {
            let mut ack = protos::EthereumTxAck::new();
            ack.set_data_chunk(data.splice(..std::cmp::min(1024, data.len()), []).collect());

            resp = self.call(ack, Box::new(|_, m: protos::EthereumTxRequest| Ok(m)))?.ok()?;
        }

        convert_signature(&resp, chain_id)
    }

    #[allow(clippy::too_many_arguments)]
    pub fn ethereum_sign_eip1559_tx(
        &mut self,
        path: Vec<u32>,
        nonce: Vec<u8>,
        gas_limit: Vec<u8>,
        to: String,
        value: Vec<u8>,
        data: Vec<u8>,
        chain_id: Option<u64>,
        max_gas_fee: Vec<u8>,
        max_priority_fee: Vec<u8>,
        access_list: Vec<AccessListItem>,
    ) -> Result<Signature> {
        let mut req = protos::EthereumSignTxEIP1559::new();
        let mut data = data;

        req.address_n = path;
        req.set_nonce(nonce);
        req.set_max_gas_fee(max_gas_fee);
        req.set_max_priority_fee(max_priority_fee);
        req.set_gas_limit(gas_limit);
        req.set_value(value);
        if let Some(chain_id) = chain_id {
            req.set_chain_id(chain_id);
        }
        req.set_to(to);

        if !access_list.is_empty() {
            req.access_list = access_list
                .into_iter()
                .map(|item| EthereumAccessList {
                    address: Some(item.address),
                    storage_keys: item.storage_keys,
                    ..Default::default()
                })
                .collect();
        }

        req.set_data_length(data.len() as u32);
        req.set_data_initial_chunk(data.splice(..std::cmp::min(1024, data.len()), []).collect());

        let mut resp =
            handle_interaction(self.call(req, Box::new(|_, m: protos::EthereumTxRequest| Ok(m)))?)?;

        while resp.data_length() > 0 {
            let mut ack = protos::EthereumTxAck::new();
            ack.set_data_chunk(data.splice(..std::cmp::min(1024, data.len()), []).collect());

            resp = self.call(ack, Box::new(|_, m: protos::EthereumTxRequest| Ok(m)))?.ok()?
        }

        convert_signature(&resp, chain_id)
    }
}

fn convert_signature(resp: &EthereumTxRequest, chain_id: Option<u64>) -> Result<Signature> {
    let mut v = resp.signature_v() as u64;
    if let Some(chain_id) = chain_id {
        if v <= 1 {
            v = v + 2 * chain_id + 35;
        }
    }
    let r = resp.signature_r().try_into().map_err(|_| Error::MalformedSignature)?;
    let s = resp.signature_r().try_into().map_err(|_| Error::MalformedSignature)?;
    Ok(Signature { r, s, v })
}
