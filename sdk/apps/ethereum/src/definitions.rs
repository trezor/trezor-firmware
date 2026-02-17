extern crate alloc;

use crate::ed25519::verify;
use crate::proto::definitions::{DefinitionType, EthereumNetworkInfo, EthereumTokenInfo};
use alloc::collections::BTreeMap;
use alloc::vec;
use alloc::vec::Vec;
use prost::Message;
use trezor_app_sdk::crypto::sha_256;

const THRESHOLD: usize = 2;
const PUBLIC_KEYS: [&[u8;32]; 3] = [
    b"\x43\x34\x99\x63\x43\x62\x3e\x46\x2f\x0f\xc9\x33\x11\xfe\xf1\x48\x4c\xa2\x3d\x2f\xf1\xee\xc6\xdf\x1f\xa8\xeb\x7e\x35\x73\xb3\xdb",
    b"\xa9\xa2\x2c\xc2\x65\xa0\xcb\x1d\x6c\xb3\x29\xbc\x0e\x60\xbc\x45\xdf\x76\xb9\xab\x28\xfb\x87\xb6\x11\x36\xfe\xaf\x8d\x8f\xdc\x96",
    b"\xb8\xd2\xb2\x1d\xe2\x71\x24\xf0\x51\x1f\x90\x3a\xe7\xe6\x0e\x07\x96\x18\x10\xa0\xb8\xf2\x8e\xa7\x55\xfa\x50\x36\x7a\x8a\x2b\x8b",
];

const MIN_DATA_VERSION: u32 = 1764611524;
const FORMAT_VERSION: &[u8] = b"trzd1";

pub struct Definitions {
    network: EthereumNetworkInfo,
    tokens: BTreeMap<Vec<u8>, EthereumTokenInfo>,
}

impl Definitions {
    pub fn new(network: EthereumNetworkInfo, tokens: BTreeMap<Vec<u8>, EthereumTokenInfo>) -> Self {
        Self { network, tokens }
    }

    pub fn from_encoded(
        encoded_network: Option<&[u8]>,
        encoded_token: Option<&[u8]>,
        chain_id: Option<u64>,
        slip44: Option<u32>,
    ) -> Result<Self, ()> {
        let mut tokens = BTreeMap::new();
        // if we have a built-in definition, use it
        let mut network = if let Some(chain_id) = chain_id {
            by_chain_id(chain_id)
        } else if let Some(slip44) = slip44 {
            by_slip44(slip44)
        } else {
            // ignore tokens if we don't have a network
            return Ok(Self::new(unknown_network(), tokens));
        };

        if network == unknown_network() && encoded_network.is_some() {
            network = decode_definition::<EthereumNetworkInfo>(encoded_network.unwrap())?;
        }

        if network == unknown_network() {
            // ignore tokens if we don't have a network
            return Ok(Self::new(unknown_network(), tokens));
        }

        if let Some(chain_id) = chain_id {
            if network.chain_id != chain_id {
                // "Network definition mismatch"
                return Err(());
            }
        }
        if let Some(slip44) = slip44 {
            if network.slip44 != slip44 {
                // "Network definition mismatch"
                return Err(());
            }
        }

        // get token definition
        if let Some(encoded_token) = encoded_token {
            let token = decode_definition::<EthereumTokenInfo>(encoded_token)?;
            // Ignore token if it doesn't match the network instead of raising an error.
            // This might help us in the future if we allow multiple networks/tokens
            // in the same message.
            if token.chain_id == network.chain_id {
                tokens.insert(token.address.clone(), token);
            }
        }

        Ok(Self::new(network, tokens))
    }

    pub fn chain_id(&self) -> u64 {
        self.network.chain_id
    }

    pub fn slip44(&self) -> u32 {
        self.network.slip44
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

    let header_len = FORMAT_VERSION.len() + 1 + 4 + 2; // format version + type + data version + payload length
    if encoded.len() < header_len {
        return Err(()); // Invalid definition
    }

    // first check format version
    if &encoded[..FORMAT_VERSION.len()] != FORMAT_VERSION {
        return Err(()); // Invalid definition
    }
    offset += FORMAT_VERSION.len();

    // second check the type of the data
    if encoded[offset] != expected_type as u8 {
        return Err(()); // Definition type mismatch
    }
    offset += 1;

    // third check data version
    let version = u32::from_le_bytes(encoded[offset..offset + 4].try_into().unwrap());
    if version < MIN_DATA_VERSION {
        return Err(()); // Definition is outdated
    }
    offset += 4;

    // get payload
    let payload_len = u16::from_le_bytes(encoded[offset..offset + 2].try_into().unwrap()) as usize;
    offset += 2;

    if encoded.len() < header_len + payload_len + 1 {
        return Err(()); // Invalid definition
    }
    let payload = &encoded[offset..offset + payload_len];
    offset += payload_len;

    // at the end compute Merkle tree root hash using
    // provided leaf data (payload with prefix) and proof

    let mut buf = vec![0u8; 1 + offset];
    buf[0] = 0x00;
    buf[1..].copy_from_slice(&encoded[..offset]);
    let mut hash = sha_256(&buf);

    let proof_len = encoded[offset];
    offset += 1;

    for _ in 0..proof_len {
        if offset + 32 > encoded.len() {
            return Err(());
        }
        let proof_entry = &encoded[offset..offset + 32];
        offset += 32;

        let (hash_a, hash_b) = if hash.as_slice() <= proof_entry {
            (hash.as_slice(), proof_entry)
        } else {
            (proof_entry, hash.as_slice())
        };

        let mut buf = vec![0u8; 1 + hash_a.len() + hash_b.len()];
        buf[0] = 0x01;
        buf[1..1 + hash_a.len()].copy_from_slice(hash_a);
        buf[1 + hash_a.len()..].copy_from_slice(hash_b);

        hash = sha_256(&buf);
    }

    if offset + 1 + 64 >= encoded.len() {
        return Err(());
    }

    let sigmask = encoded[offset];
    offset += 1;

    let signature: &[u8; 64] = (&encoded[offset..offset + 64]).try_into().unwrap();

    // verify signature
    let result = verify(signature, &hash, THRESHOLD, &PUBLIC_KEYS, sigmask).map_err(|_| ())?;
    if !result {
        // TODO Invalid definition signature
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
        (1, 60, "ETH", "Ethereum"),
        (10, 614, "ETH", "Optimism"),
        (56, 714, "BNB", "BNB Smart Chain"),
        (61, 61, "ETC", "Ethereum Classic"),
        (137, 966, "POL", "Polygon"),
        (8453, 8453, "ETH", "Base"),
        (42161, 9001, "ETH", "Arbitrum One"),
        (560048, 60, "tHOD", "Hoodi"),
        (11155111, 60, "tSEP", "Sepolia"),
    ]
}
