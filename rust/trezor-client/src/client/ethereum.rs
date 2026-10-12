use super::{handle_interaction, Trezor};
use crate::{
    error::Result,
    messages::TrezorMessage,
    protos::{
        self, ethereum_sign_tx_eip1559::EthereumAccessList, EthereumTxRequest, MessageType::*,
    },
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

/// A source of signed Trezor definitions (network, token and clear-signing
/// display-format blobs) used to answer `EthereumDefinitionRequest`s from the
/// device.
///
/// Implementations typically fetch from
/// `https://data.trezor.io/firmware/definitions/`, a local directory, or an
/// in-memory cache. See `docs/common/external-definitions.md`. All methods
/// return `None` by default, meaning no definition is available for the lookup.
pub trait DefinitionSource {
    /// Signed network definition for `chain_id`.
    fn get_eth_network(&self, chain_id: u64) -> Option<Vec<u8>> {
        let _ = chain_id;
        None
    }

    /// Signed token definition for `(chain_id, token_address)`.
    fn get_eth_token(&self, chain_id: u64, token_address: &[u8]) -> Option<Vec<u8>> {
        let _ = (chain_id, token_address);
        None
    }

    /// Signed clear-signing display-format descriptor for a contract and
    /// function selector.
    fn get_eth_display_format(
        &self,
        chain_id: u64,
        contract_address: &[u8],
        func_sig: &[u8],
    ) -> Option<Vec<u8>> {
        let _ = (chain_id, contract_address, func_sig);
        None
    }
}

/// A [`DefinitionSource`] backed by a local directory laid out like the
/// `data.trezor.io/firmware/definitions` tree, for example:
///
/// ```text
/// <root>/eth/chain-id/1/network.dat
/// <root>/eth/chain-id/1/token-<address>.dat
/// <root>/eth/chain-id/1/display-format/<contract>-<func_sig>.dat
/// ```
pub struct FilesystemSource {
    root: std::path::PathBuf,
}

impl FilesystemSource {
    /// Create a source rooted at `root`.
    pub fn new(root: impl Into<std::path::PathBuf>) -> Self {
        Self { root: root.into() }
    }

    fn read(&self, parts: &[&str]) -> Option<Vec<u8>> {
        let mut path = self.root.clone();
        for part in parts {
            path.push(part);
        }
        std::fs::read(path).ok()
    }
}

impl DefinitionSource for FilesystemSource {
    fn get_eth_network(&self, chain_id: u64) -> Option<Vec<u8>> {
        self.read(&["eth", "chain-id", &chain_id.to_string(), "network.dat"])
    }

    fn get_eth_token(&self, chain_id: u64, token_address: &[u8]) -> Option<Vec<u8>> {
        let name = format!("token-{}.dat", hex::encode(token_address));
        self.read(&["eth", "chain-id", &chain_id.to_string(), &name])
    }

    fn get_eth_display_format(
        &self,
        chain_id: u64,
        contract_address: &[u8],
        func_sig: &[u8],
    ) -> Option<Vec<u8>> {
        let name = format!("{}-{}.dat", hex::encode(contract_address), hex::encode(func_sig));
        self.read(&["eth", "chain-id", &chain_id.to_string(), "display-format", &name])
    }
}

/// Build an `EthereumDefinitionAck` from `source`, mirroring trezorlib's
/// `_answer_definition_request`. A `func_sig` request asks for a clear-signing
/// display format; otherwise the network and token definitions are served.
fn answer_definition_request(
    source: Option<&dyn DefinitionSource>,
    req: &protos::EthereumDefinitionRequest,
) -> protos::EthereumDefinitionAck {
    let mut ack = protos::EthereumDefinitionAck::new();
    let Some(source) = source else {
        return ack;
    };

    if !req.func_sig().is_empty() {
        if let Some(display_format) =
            source.get_eth_display_format(req.chain_id(), req.token_address(), req.func_sig())
        {
            let mut definitions = protos::EthereumDefinitions::new();
            definitions.set_encoded_display_format(display_format);
            ack.definitions = protobuf::MessageField::some(definitions);
        }
        return ack;
    }

    let network = source.get_eth_network(req.chain_id());
    let token = if req.has_token_address() {
        source.get_eth_token(req.chain_id(), req.token_address())
    } else {
        None
    };
    if network.is_some() || token.is_some() {
        let mut definitions = protos::EthereumDefinitions::new();
        if let Some(network) = network {
            definitions.set_encoded_network(network);
        }
        if let Some(token) = token {
            definitions.set_encoded_token(token);
        }
        ack.definitions = protobuf::MessageField::some(definitions);
    }
    ack
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
                    return Err(Error::MalformedSignature);
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
        self.ethereum_sign_tx_inner(
            path, nonce, gas_price, gas_limit, to, value, data, chain_id, None, None,
        )
    }

    /// Legacy signing with signed network/token definitions (from
    /// data.trezor.io) so the device can display unknown tokens and networks.
    #[allow(clippy::too_many_arguments)]
    pub fn ethereum_sign_tx_with_definitions(
        &mut self,
        path: Vec<u32>,
        nonce: Vec<u8>,
        gas_price: Vec<u8>,
        gas_limit: Vec<u8>,
        to: String,
        value: Vec<u8>,
        data: Vec<u8>,
        chain_id: Option<u64>,
        definitions: Option<protos::EthereumDefinitions>,
    ) -> Result<Signature> {
        self.ethereum_sign_tx_inner(
            path,
            nonce,
            gas_price,
            gas_limit,
            to,
            value,
            data,
            chain_id,
            definitions,
            None,
        )
    }

    /// Legacy signing with a dynamic [`DefinitionSource`]. The device is told
    /// that the host supports definition requests, and any
    /// `EthereumDefinitionRequest` it sends mid-flow is answered from `source`.
    #[allow(clippy::too_many_arguments)]
    pub fn ethereum_sign_tx_with_source(
        &mut self,
        path: Vec<u32>,
        nonce: Vec<u8>,
        gas_price: Vec<u8>,
        gas_limit: Vec<u8>,
        to: String,
        value: Vec<u8>,
        data: Vec<u8>,
        chain_id: Option<u64>,
        source: &dyn DefinitionSource,
    ) -> Result<Signature> {
        self.ethereum_sign_tx_inner(
            path,
            nonce,
            gas_price,
            gas_limit,
            to,
            value,
            data,
            chain_id,
            None,
            Some(source),
        )
    }

    #[allow(clippy::too_many_arguments)]
    fn ethereum_sign_tx_inner(
        &mut self,
        path: Vec<u32>,
        nonce: Vec<u8>,
        gas_price: Vec<u8>,
        gas_limit: Vec<u8>,
        to: String,
        value: Vec<u8>,
        data: Vec<u8>,
        chain_id: Option<u64>,
        definitions: Option<protos::EthereumDefinitions>,
        source: Option<&dyn DefinitionSource>,
    ) -> Result<Signature> {
        let mut req = protos::EthereumSignTx::new();
        if let Some(definitions) = definitions {
            req.definitions = protobuf::MessageField::some(definitions);
        }
        if source.is_some() {
            req.set_supports_definition_request(true);
        }
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

        self.ethereum_sign_loop(req, data, chain_id, source)
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
        self.ethereum_sign_eip1559_tx_inner(
            path,
            nonce,
            gas_limit,
            to,
            value,
            data,
            chain_id,
            max_gas_fee,
            max_priority_fee,
            access_list,
            None,
            None,
        )
    }

    /// EIP-1559 signing with signed network/token definitions (from
    /// data.trezor.io) so the device can display unknown tokens and networks.
    #[allow(clippy::too_many_arguments)]
    pub fn ethereum_sign_eip1559_tx_with_definitions(
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
        definitions: Option<protos::EthereumDefinitions>,
    ) -> Result<Signature> {
        self.ethereum_sign_eip1559_tx_inner(
            path,
            nonce,
            gas_limit,
            to,
            value,
            data,
            chain_id,
            max_gas_fee,
            max_priority_fee,
            access_list,
            definitions,
            None,
        )
    }

    /// EIP-1559 signing with a dynamic [`DefinitionSource`], see
    /// [`Self::ethereum_sign_tx_with_source`].
    #[allow(clippy::too_many_arguments)]
    pub fn ethereum_sign_eip1559_tx_with_source(
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
        source: &dyn DefinitionSource,
    ) -> Result<Signature> {
        self.ethereum_sign_eip1559_tx_inner(
            path,
            nonce,
            gas_limit,
            to,
            value,
            data,
            chain_id,
            max_gas_fee,
            max_priority_fee,
            access_list,
            None,
            Some(source),
        )
    }

    #[allow(clippy::too_many_arguments)]
    fn ethereum_sign_eip1559_tx_inner(
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
        definitions: Option<protos::EthereumDefinitions>,
        source: Option<&dyn DefinitionSource>,
    ) -> Result<Signature> {
        let mut req = protos::EthereumSignTxEIP1559::new();
        if let Some(definitions) = definitions {
            req.definitions = protobuf::MessageField::some(definitions);
        }
        if source.is_some() {
            req.set_supports_definition_request(true);
        }
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

        self.ethereum_sign_loop(req, data, chain_id, source)
    }

    /// Shared request/response loop for the Ethereum signing flows. Handles
    /// data-chunk requests as well as definition requests, mirroring trezorlib's
    /// `_ethereum_sign_loop`.
    fn ethereum_sign_loop<S: TrezorMessage>(
        &mut self,
        initial: S,
        mut data: Vec<u8>,
        chain_id: Option<u64>,
        source: Option<&dyn DefinitionSource>,
    ) -> Result<Signature> {
        let mut resp = self.call_raw_interactive(initial)?;
        loop {
            match resp.message_type() {
                MessageType_EthereumTxRequest => {
                    let msg: protos::EthereumTxRequest = resp.into_message()?;
                    if msg.data_length() > 0 {
                        let mut ack = protos::EthereumTxAck::new();
                        ack.set_data_chunk(
                            data.splice(..std::cmp::min(1024, data.len()), []).collect(),
                        );
                        resp = self.call_raw_interactive(ack)?;
                    } else {
                        return convert_signature(&msg, chain_id);
                    }
                }
                MessageType_EthereumDefinitionRequest => {
                    let req: protos::EthereumDefinitionRequest = resp.into_message()?;
                    let ack = answer_definition_request(source, &req);
                    resp = self.call_raw_interactive(ack)?;
                }
                m => return Err(Error::UnexpectedMessageType(m)),
            }
        }
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
    let s = resp.signature_s().try_into().map_err(|_| Error::MalformedSignature)?;
    Ok(Signature { r, s, v })
}

#[cfg(test)]
mod tests {
    use super::*;

    struct MockSource;

    impl DefinitionSource for MockSource {
        fn get_eth_network(&self, chain_id: u64) -> Option<Vec<u8>> {
            (chain_id == 1).then(|| vec![1, 2, 3])
        }

        fn get_eth_token(&self, chain_id: u64, token_address: &[u8]) -> Option<Vec<u8>> {
            (chain_id == 1 && token_address == [0xaa; 20]).then(|| vec![4, 5, 6])
        }

        fn get_eth_display_format(
            &self,
            _chain_id: u64,
            _contract_address: &[u8],
            func_sig: &[u8],
        ) -> Option<Vec<u8>> {
            (func_sig == [0xde, 0xad, 0xbe, 0xef]).then(|| vec![7, 8, 9])
        }
    }

    #[test]
    fn answer_network_and_token_request() {
        let mut req = protos::EthereumDefinitionRequest::new();
        req.set_chain_id(1);
        req.set_token_address(vec![0xaa; 20]);
        let ack = answer_definition_request(Some(&MockSource), &req);
        assert_eq!(ack.definitions.encoded_network(), &[1, 2, 3]);
        assert_eq!(ack.definitions.encoded_token(), &[4, 5, 6]);
        assert!(!ack.definitions.has_encoded_display_format());
    }

    #[test]
    fn answer_display_format_request() {
        let mut req = protos::EthereumDefinitionRequest::new();
        req.set_chain_id(1);
        req.set_token_address(vec![0xbb; 20]);
        req.set_func_sig(vec![0xde, 0xad, 0xbe, 0xef]);
        let ack = answer_definition_request(Some(&MockSource), &req);
        assert_eq!(ack.definitions.encoded_display_format(), &[7, 8, 9]);
        assert!(!ack.definitions.has_encoded_network());
        assert!(!ack.definitions.has_encoded_token());
    }

    #[test]
    fn answer_unknown_request_is_empty() {
        let mut req = protos::EthereumDefinitionRequest::new();
        req.set_chain_id(999);
        req.set_token_address(vec![0xcc; 20]);
        let ack = answer_definition_request(Some(&MockSource), &req);
        assert!(!ack.definitions.has_encoded_network());
        assert!(!ack.definitions.has_encoded_token());
        assert!(!ack.definitions.has_encoded_display_format());
    }

    #[test]
    fn answer_without_source_is_empty() {
        let mut req = protos::EthereumDefinitionRequest::new();
        req.set_chain_id(1);
        req.set_token_address(vec![0xaa; 20]);
        let ack = answer_definition_request(None, &req);
        assert!(!ack.definitions.has_encoded_network());
        assert!(!ack.definitions.has_encoded_token());
    }
}
