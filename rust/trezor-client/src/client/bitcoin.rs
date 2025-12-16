use super::{Trezor, TrezorResponse};
use crate::{error::Result, flows::sign_tx::SignTxProgress, protos, utils};
use bitcoin::{
    address::NetworkUnchecked, bip32, network::Network, psbt,
    secp256k1::ecdsa::RecoverableSignature, Address,
};

pub use crate::protos::InputScriptType;

#[derive(PartialEq, Eq)]
pub struct WalletPubKey {
    pub inner: bip32::Xpub,
    pub source: bip32::KeySource,
}

impl std::str::FromStr for WalletPubKey {
    type Err = bip32::Error;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let (keysource_str, xpub_str) = s
            .strip_prefix('[')
            .and_then(|s| s.rsplit_once(']'))
            .ok_or(bip32::Error::InvalidDerivationPathFormat)?;
        let (f_str, path_str) = keysource_str.split_once('/').unwrap_or((keysource_str, ""));
        let fingerprint = bip32::Fingerprint::from_str(f_str)
            .map_err(|_| bip32::Error::InvalidDerivationPathFormat)?;
        let derivation_path = if path_str.is_empty() {
            bip32::DerivationPath::master()
        } else {
            bip32::DerivationPath::from_str(&format!("m/{}", path_str))?
        };
        Ok(WalletPubKey {
            inner: bip32::Xpub::from_str(xpub_str)?,
            source: (fingerprint, derivation_path),
        })
    }
}

impl core::fmt::Display for WalletPubKey {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        let (fg, path) = &self.source;
        if path.is_master() {
            write!(f, "[{}]{}", fg, self.inner,)
        } else {
            write!(f, "[{}/{}]{}", fg, path, self.inner,)
        }
    }
}

impl Trezor {
    pub fn get_public_key(
        &mut self,
        path: &bip32::DerivationPath,
        script_type: InputScriptType,
        network: Network,
        show_display: bool,
    ) -> Result<TrezorResponse<'_, bip32::Xpub, protos::PublicKey>> {
        let mut req = protos::GetPublicKey::new();
        req.address_n = utils::convert_path(path);
        req.set_show_display(show_display);
        req.set_coin_name(utils::coin_name(network)?);
        req.set_script_type(script_type);
        self.call(req, Box::new(|_, m| Ok(m.xpub().parse()?)))
    }

    //TODO(stevenroose) multisig
    pub fn get_address(
        &mut self,
        path: &bip32::DerivationPath,
        script_type: InputScriptType,
        network: Network,
        show_display: bool,
    ) -> Result<TrezorResponse<'_, Address, protos::Address>> {
        let mut req = protos::GetAddress::new();
        req.address_n = utils::convert_path(path);
        req.set_coin_name(utils::coin_name(network)?);
        req.set_show_display(show_display);
        req.set_script_type(script_type);
        self.call(req, Box::new(|_, m| parse_address(m.address())))
    }

    pub fn register_policy(
        &mut self,
        name: String,
        template: String,
        primary: WalletPubKey,
        recovery: WalletPubKey,
        recovery_delay: u32,
    ) -> Result<TrezorResponse<'_, Option<Vec<u8>>, protos::PolicyRegistration>> {
        let mut req = protos::Policy::new();
        req.set_name(name);
        req.set_template(template);
        req.xpubs.push(primary.to_string());
        req.xpubs.push(recovery.to_string());
        req.set_blocks(recovery_delay);
        req.set_coin_name(utils::coin_name(bitcoin::Network::Testnet)?);
        self.call(req, Box::new(|_, m| Ok(m.mac)))
    }

    pub fn get_policy_address(
        &mut self,
        name: String,
        template: String,
        primary: WalletPubKey,
        recovery: WalletPubKey,
        recovery_delay: u32,
        mac: Vec<u8>,
        index: u32,
        change: bool,
        network: Network,
        show_display: bool,
    ) -> Result<TrezorResponse<'_, Address, protos::Address>> {
        let mut req = protos::GetPolicyAddress::new();

        let policy = req.policy.mut_or_insert_default();
        policy.set_name(name);
        policy.set_template(template);
        policy.xpubs.push(primary.to_string());
        policy.xpubs.push(recovery.to_string());
        policy.set_blocks(recovery_delay);
        policy.set_coin_name(utils::coin_name(network)?);


        req.set_mac(mac);
        req.set_index(index);
        req.set_change(change);
        req.set_show_display(show_display);
        req.set_coin_name(utils::coin_name(network)?);

        self.call(req, Box::new(|_, m| parse_address(m.address())))
    }

    pub fn sign_tx(
        &mut self,
        psbt: &psbt::Psbt,
        network: Network,
    ) -> Result<TrezorResponse<'_, SignTxProgress<'_>, protos::TxRequest>> {
        let tx = &psbt.unsigned_tx;
        let mut req = protos::SignTx::new();
        req.set_inputs_count(tx.input.len() as u32);
        req.set_outputs_count(tx.output.len() as u32);
        req.set_coin_name(utils::coin_name(network)?);
        req.set_version(tx.version.0 as u32);
        req.set_lock_time(tx.lock_time.to_consensus_u32());
        self.call(req, Box::new(|c, m| Ok(SignTxProgress::new(c, m))))
    }

    pub fn sign_message(
        &mut self,
        message: String,
        path: &bip32::DerivationPath,
        script_type: InputScriptType,
        network: Network,
    ) -> Result<TrezorResponse<'_, (Address, RecoverableSignature), protos::MessageSignature>> {
        let mut req = protos::SignMessage::new();
        req.address_n = utils::convert_path(path);
        // Normalize to Unicode NFC.
        let msg_bytes = nfc_normalize(&message).into_bytes();
        req.set_message(msg_bytes);
        req.set_coin_name(utils::coin_name(network)?);
        req.set_script_type(script_type);
        self.call(
            req,
            Box::new(|_, m| {
                let address = parse_address(m.address())?;
                let signature = utils::parse_recoverable_signature(m.signature())?;
                Ok((address, signature))
            }),
        )
    }
}

fn parse_address(s: &str) -> Result<Address> {
    let address = s.parse::<Address<NetworkUnchecked>>()?;
    Ok(address.assume_checked())
}

// Modified from:
// https://github.com/rust-lang/rust/blob/2a8221dbdfd180a2d56d4b0089f4f3952d8c2bcd/compiler/rustc_parse/src/lexer/mod.rs#LL754C5-L754C5
fn nfc_normalize(string: &str) -> String {
    use unicode_normalization::{is_nfc_quick, IsNormalized, UnicodeNormalization};
    match is_nfc_quick(string.chars()) {
        IsNormalized::Yes => string.to_string(),
        _ => string.chars().nfc().collect::<String>(),
    }
}
