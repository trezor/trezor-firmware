use crate::{
    alloc_types::{String, Vec},
    paths::Bip32Path,
    proto::{
        common::{HdNodeType, button_request::ButtonRequestType},
        ethereum::{GetPublicKey, PublicKey},
    },
    strutil::hex_encode,
};
use trezor_app_sdk::{Error, Result, ResultExt, crypto, ui, unwrap};

pub(crate) fn get_public_key(msg: GetPublicKey) -> Result<PublicKey> {
    const VERSION: u32 = 0x0488B21E;

    let dp = Bip32Path::from_slice(&msg.address_n);

    // let xpub = crypto::get_xpub(&msg.address_n).context("Failed to get xpub")?;
    let xpub_bytes = crypto::get_xpub_bytes(dp.as_ref()).context("Failed to get xpub bytes")?;

    // TODO: temporary, replace with app metadata once available
    let xpub_serialized = crypto::get_xpub(dp.as_ref()).context("Failed to get xpub")?;
    let hdnode = HdNodeData::deserialize_public(&xpub_serialized, VERSION)
        .context("Failed to deserialize xpub")?;
    let (depth, fingerprint, child_num, chain_code) = (
        u32::from(hdnode.depth),
        hdnode.fingerprint,
        hdnode.child_num,
        hdnode.chain_code,
    );

    let xpub = hdnode.serialize_public(VERSION)?;

    let public_key = PublicKey {
        xpub,
        node: HdNodeType {
            depth,
            fingerprint,
            child_num,
            chain_code: chain_code.to_vec(),
            public_key: xpub_bytes.to_vec(),
            ..Default::default()
        },
    };

    if matches!(msg.show_display, Some(true)) {
        let xpub = hex_encode(&public_key.node.public_key)
            .map_err(|_| Error::DataError("Failed to hex-encode message"))?;
        ui::error_if_not_confirmed(ui::show_public_key(ui::ShowPublicKey::new(
            xpub.as_str(),
            tr!("address__public_key"),
            None,
            None,
            None,
            "show_pubkey",
            ButtonRequestType::Other.into(),
        ))?)
        .context("Public key was not confirmed")?;

        ui::show_success(ui::ShowSuccess::new(
            tr!("words__title_done"),
            tr!("address__public_key_confirmed"),
            tr!("instructions__continue_in_app"),
            Some(3200),
            None,
            ButtonRequestType::Other.into(),
        ))?;
    }

    Ok(public_key)
}

/// Parsed fields of a serialized extended public key (xpub) in BIP-32 format.
struct HdNodeData {
    /// Depth of the key in the derivation tree.
    depth: u8,
    /// Fingerprint of the parent key.
    fingerprint: u32,
    /// Child key index.
    child_num: u32,
    /// 32-byte chain code.
    chain_code: [u8; 32],
    /// 33-byte compressed public key.
    public_key: [u8; 33],
}

impl HdNodeData {
    const VERSION_LEN: usize = 4;
    const DEPTH_LEN: usize = 1;
    const FINGERPRINT_LEN: usize = 4;
    const CHILD_NUM_LEN: usize = 4;
    const CHAIN_CODE_LEN: usize = 32;
    const PUBLIC_KEY_LEN: usize = 33;
    const TOTAL: usize = Self::VERSION_LEN
        + Self::DEPTH_LEN
        + Self::FINGERPRINT_LEN
        + Self::CHILD_NUM_LEN
        + Self::CHAIN_CODE_LEN
        + Self::PUBLIC_KEY_LEN
        + 4; // 4 bytes for checksum

    /// Deserializes a base58-encoded extended public key.
    ///
    /// Validates the total length and the expected `version` prefix.
    ///
    /// # Errors
    ///
    /// Returns `Err(())` if the base58 decoding fails, the decoded length is wrong,
    /// or the version does not match.
    pub fn deserialize_public(serialized: &str, version: u32) -> Result<Self> {
        let mut node_data = [0u8; Self::TOTAL];

        let decoded_len = bs58::decode(serialized)
            .onto(&mut node_data)
            .map_err(|_| Error::DataError("Failed to decode xpub"))?;
        if decoded_len != Self::TOTAL {
            return Err(Error::DataError("Invalid xpub length"));
        }

        let (ver_bytes, rest) = node_data.split_at(Self::VERSION_LEN);
        let ver = u32::from_be_bytes(unwrap!(ver_bytes.try_into()));
        if ver != version {
            return Err(Error::DataError("Version mismatch in xpub"));
        }

        let (depth_bytes, rest) = rest.split_at(Self::DEPTH_LEN);
        let depth = u8::from_be_bytes(unwrap!(depth_bytes.try_into()));

        let (fingerprint_bytes, rest) = rest.split_at(Self::FINGERPRINT_LEN);
        let fingerprint = u32::from_be_bytes(unwrap!(fingerprint_bytes.try_into()));

        let (child_num_bytes, rest) = rest.split_at(Self::CHILD_NUM_LEN);
        let child_num = u32::from_be_bytes(unwrap!(child_num_bytes.try_into()));

        let (chain_code_bytes, rest) = rest.split_at(Self::CHAIN_CODE_LEN);
        let chain_code: [u8; 32] = unwrap!(chain_code_bytes.try_into());

        let (public_key_bytes, _checksum) = rest.split_at(Self::PUBLIC_KEY_LEN);
        let public_key: [u8; 33] = unwrap!(public_key_bytes.try_into());

        Ok(HdNodeData {
            depth,
            fingerprint,
            child_num,
            chain_code,
            public_key,
        })
    }

    /// Double SHA-256: SHA256(SHA256(data)), returns first 4 bytes as checksum.
    fn sha256d_checksum(data: &[u8]) -> [u8; 4] {
        let mut hasher = crypto::Sha256::new(Some(data));
        let first = hasher.digest();

        let mut hasher = crypto::Sha256::new(Some(&first));
        let second = hasher.digest();

        [second[0], second[1], second[2], second[3]]
    }

    pub fn serialize_public(&self, version: u32) -> Result<String> {
        let mut node_data = Vec::with_capacity(Self::TOTAL);

        node_data.extend(&version.to_be_bytes());
        node_data.extend(&self.depth.to_be_bytes());
        node_data.extend(&self.fingerprint.to_be_bytes());
        node_data.extend(&self.child_num.to_be_bytes());
        node_data.extend(&self.chain_code);
        node_data.extend(&self.public_key);

        let checksum = Self::sha256d_checksum(&node_data);
        node_data.extend(&checksum);

        if node_data.len() != Self::TOTAL {
            return Err(Error::DataError("Invalid node data length"));
        }

        Ok(bs58::encode(&node_data).into_string())
    }
}
