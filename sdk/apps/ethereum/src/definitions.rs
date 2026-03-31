use crate::{
    common::COIN,
    ed25519,
    proto::definitions::{DefinitionType, EthereumNetworkInfo, EthereumTokenInfo},
    tokens::{token_by_chain_address, unknown_token},
    uformat,
};
#[cfg(not(test))]
use alloc::string::String;
use prost::Message;
#[cfg(test)]
use std::string::String;
use trezor_app_sdk::{crypto::Sha256, info};

const THRESHOLD: usize = 2;
const PUBLIC_KEYS: [&[u8;32]; 3] = [
    b"\x43\x34\x99\x63\x43\x62\x3e\x46\x2f\x0f\xc9\x33\x11\xfe\xf1\x48\x4c\xa2\x3d\x2f\xf1\xee\xc6\xdf\x1f\xa8\xeb\x7e\x35\x73\xb3\xdb",
    b"\xa9\xa2\x2c\xc2\x65\xa0\xcb\x1d\x6c\xb3\x29\xbc\x0e\x60\xbc\x45\xdf\x76\xb9\xab\x28\xfb\x87\xb6\x11\x36\xfe\xaf\x8d\x8f\xdc\x96",
    b"\xb8\xd2\xb2\x1d\xe2\x71\x24\xf0\x51\x1f\x90\x3a\xe7\xe6\x0e\x07\x96\x18\x10\xa0\xb8\xf2\x8e\xa7\x55\xfa\x50\x36\x7a\x8a\x2b\x8b",
];

const DEV_PUBLIC_KEYS: [&[u8;32]; 3] = [
        b"\x68\x46\x0e\xbe\xf3\xb1\x38\x16\x4e\xc7\xfd\x86\x10\xe9\x58\x00\xdf\x75\x98\xf7\x0f\x2f\x2e\xa7\xdb\x51\x72\xac\x74\xeb\xc1\x44",
        b"\x8d\x4a\xbe\x07\x4f\xef\x92\x29\xd3\xb4\x41\xdf\xea\x4f\x98\xf8\x05\xb1\xa2\xb3\xa0\x6a\xe6\x45\x81\x0e\xfe\xce\x77\xfd\x50\x44",
        b"\x97\xf7\x13\x5a\x9a\x26\x90\xe7\x3b\xeb\x26\x55\x6f\x1c\xb1\x63\xbe\xa2\x53\x2a\xff\xa1\xe7\x78\x24\x30\xbe\x98\xc0\xe5\x68\x12",
    ];

const MIN_DATA_VERSION: u32 = 1764611524;
const FORMAT_VERSION: &[u8] = b"trzd1";

pub struct Definitions {
    pub network: EthereumNetworkInfo,
    pub token: Option<EthereumTokenInfo>,
}

impl Definitions {
    pub fn new(network: EthereumNetworkInfo, token: Option<EthereumTokenInfo>) -> Self {
        Self { network, token }
    }

    pub fn from_encoded(
        encoded_network: Option<&[u8]>,
        encoded_token: Option<&[u8]>,
        chain_id: Option<u64>,
        slip44: Option<u32>,
    ) -> Result<Self, ()> {
        // if we have a built-in definition, use it
        let mut token = None;
        let mut network = if let Some(chain_id) = chain_id {
            by_chain_id(chain_id)
        } else if let Some(slip44) = slip44 {
            by_slip44(slip44)
        } else {
            // ignore tokens if we don't have a network
            return Ok(Self::new(unknown_network(), token));
        };

        if network == unknown_network() {
            if let Some(encoded_network) = encoded_network {
                info!("Decoding network definition from the message");
                network = decode_definition::<EthereumNetworkInfo>(encoded_network)?;
                info!("Decoded network definition: ");
            }
        }

        if network == unknown_network() {
            // ignore tokens if we don't have a network
            return Ok(Self::new(unknown_network(), token));
        }

        if let Some(chain_id) = chain_id {
            info!(
                "chain id: {} network chain id: {}",
                chain_id, network.chain_id
            );
            if network.chain_id != chain_id {
                // "Network definition mismatch"
                return Err(());
            }
        }
        if let Some(slip44) = slip44 {
            info!("Network definition mismatch slip44");
            if network.slip44 != slip44 {
                // "Network definition mismatch"
                return Err(());
            }
        }

        // get token definition
        if let Some(encoded_token) = encoded_token {
            info!("Decoding token definition from the message");
            let token_info = decode_definition::<EthereumTokenInfo>(encoded_token)?;
            // Ignore token if it doesn't match the network instead of raising an error.
            // This might help us in the future if we allow multiple networks/tokens
            // in the same message.
            if token_info.chain_id == network.chain_id {
                token = Some(token_info);
            }
        }

        Ok(Self::new(network, token))
    }

    pub fn network(&self) -> &EthereumNetworkInfo {
        &self.network
    }

    // pub fn chain_id(&self) -> u64 {
    //     self.network.chain_id
    // }

    pub fn slip44(&self) -> u32 {
        self.network.slip44
    }

    pub fn get_token(&self, address: &[u8]) -> EthereumTokenInfo {
        // if we have a built-in definition, use it
        let token = token_by_chain_address(self.network.chain_id, address);

        if let Some(token_info) = token {
            return token_info;
        }

        if let Some(token_info) = self.token.iter().find(|t| t.address.as_slice() == address) {
            token_info.clone()
        } else {
            unknown_token()
        }
    }
}

trait DefinitionMessage: Message + Default {
    fn definition_type() -> DefinitionType;
}

impl DefinitionMessage for EthereumNetworkInfo {
    fn definition_type() -> DefinitionType {
        DefinitionType::EthereumNetwork
    }
}

impl DefinitionMessage for EthereumTokenInfo {
    fn definition_type() -> DefinitionType {
        DefinitionType::EthereumToken
    }
}

fn decode_definition<A: DefinitionMessage>(encoded: &[u8]) -> Result<A, ()> {
    let expected_type = A::definition_type();

    let mut offset = 0;
    let mut remaining = encoded.len();

    let header_len = FORMAT_VERSION.len() + 1 + 4 + 2; // format version + type + data version + payload length
    info!("encoded len {} header len {}", remaining, header_len);
    if remaining < header_len {
        return Err(()); // Invalid definition
    }

    // first check format version
    if &encoded[offset..offset + FORMAT_VERSION.len()] != FORMAT_VERSION {
        info!("Definition format version mismatch");
        return Err(()); // Invalid definition
    }
    offset += FORMAT_VERSION.len();
    remaining -= FORMAT_VERSION.len();

    // second check the type of the data
    if encoded[offset] != expected_type as u8 {
        info!("Definition type mismatch");

        return Err(()); // Definition type mismatch
    }
    offset += 1;
    remaining -= 1;

    // third check data version
    info!("getting version from definition");
    let version = u32::from_le_bytes(encoded[offset..offset + 4].try_into().map_err(|_| ())?);
    info!("definition version: {}", version);
    if version < MIN_DATA_VERSION {
        info!("Definition data version too old");
        return Err(()); // Definition is outdated
    }
    offset += 4;
    remaining -= 4;

    // get payload
    info!("getting payload from definition");
    let payload_len =
        u16::from_le_bytes(encoded[offset..offset + 2].try_into().map_err(|_| ())?) as usize;
    info!("definition payload length: {}", payload_len);
    offset += 2;
    remaining -= 2;

    if remaining < (payload_len + 1) {
        info!("Definition payload length mismatch");
        return Err(()); // Invalid definition
    }
    let payload = &encoded[offset..offset + payload_len];
    offset += payload_len;
    remaining -= payload_len;

    // at the end compute Merkle tree root hash using
    // provided leaf data (payload with prefix) and proof

    info!("Computing definition hash");
    let mut hasher = Sha256::new(Some(b"\x00"));
    hasher.update(&encoded[..offset]);
    let mut hash = hasher.digest();

    let proof_len = encoded[offset];
    offset += 1;
    remaining -= 1;

    for _ in 0..proof_len {
        if remaining < 32 {
            info!("Definition proof length mismatch");
            return Err(());
        }
        let proof_entry = &encoded[offset..offset + 32];
        offset += 32;
        remaining -= 32;

        let (hash_a, hash_b) = if hash.as_slice() <= proof_entry {
            (hash.as_slice(), proof_entry)
        } else {
            (proof_entry, hash.as_slice())
        };

        info!("Updating definition hash with proof entry");
        let mut hasher = Sha256::new(Some(b"\x01"));
        hasher.update(&hash_a);
        hasher.update(&hash_b);
        hash = hasher.digest();
    }

    if remaining < 1 + 64 {
        info!("Definition signature length mismatch");
        return Err(());
    }

    let sigmask = encoded[offset];
    offset += 1;
    remaining -= 1;

    let signature: &[u8; 64] = (&encoded[offset..offset + 64]).try_into().map_err(|_| ())?;
    // offset += 64;
    remaining -= 64;

    info!("remaining after parsing definition: {}", remaining);
    if remaining != 0 {
        info!("Definition has extra data at the end");
        return Err(()); // Invalid definition
    }

    let mut hash_str = String::new();
    for byte in hash.as_slice() {
        hash_str.push_str(&uformat!("{} ", *byte));
    }
    let mut sig_str = String::new();
    for byte in signature {
        sig_str.push_str(&uformat!("{} ", *byte));
    }
    info!("Definition signature: {}", sig_str.as_str());
    info!("Definition hash: {}", hash_str.as_str());
    info!("Definition sigmask: {}", sigmask);
    info!("Definition threshold: {}", THRESHOLD);

    // verify signature
    info!("Verifying definition signature");
    // TODO: use real signature verification instead of dummy implementation
    let result =
        ed25519::verify(signature, &hash, THRESHOLD, &DEV_PUBLIC_KEYS, sigmask).map_err(|_| ())?;

    info!("Definition signature verification result: {}", result);
    if !result {
        info!("Invalid definition signature");
        return Err(());
    }

    // decode it if it's OK
    A::decode(payload).map_err(|_| ())
}

pub fn unknown_network() -> EthereumNetworkInfo {
    EthereumNetworkInfo {
        chain_id: 0,
        symbol: "UNKN".into(),
        slip44: 0,
        name: "Unknown Network".into(),
    }
}

pub fn by_chain_id(chain_id: u64) -> EthereumNetworkInfo {
    for (c, s, sym, n) in _networks_iterator() {
        if *c == chain_id {
            return EthereumNetworkInfo {
                chain_id: *c,
                slip44: *s,
                symbol: (*sym).into(),
                name: (*n).into(),
            };
        }
    }
    unknown_network()
}

pub fn by_slip44(slip44: u32) -> EthereumNetworkInfo {
    for (c, s, sym, n) in _networks_iterator() {
        if *s == slip44 {
            return EthereumNetworkInfo {
                chain_id: *c,
                slip44: *s,
                symbol: (*sym).into(),
                name: (*n).into(),
            };
        }
    }
    unknown_network()
}

fn _networks_iterator() -> &'static [(u64, u32, &'static str, &'static str)] {
    &[
        (1, 60, COIN, "Ethereum"),
        (10, 614, COIN, "Optimism"),
        (56, 714, "BNB", "BNB Smart Chain"),
        (61, 61, COIN, "Ethereum Classic"),
        (137, 966, "POL", "Polygon"),
        (8453, 8453, COIN, "Base"),
        (42161, 9001, COIN, "Arbitrum One"),
        (560048, 60, "tHOD", "Hoodi"),
        (11155111, 60, "tSEP", "Sepolia"),
    ]
}
