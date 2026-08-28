use std::collections::HashMap;

use super::{Trezor, TrezorResponse};
use crate::{error::Result, flows::sign_tx::SignTxProgress, protos, utils};
use bitcoin::{
    address::NetworkUnchecked, bip32, network::Network, psbt,
    secp256k1::ecdsa::RecoverableSignature, Address,
};

pub use crate::protos::InputScriptType;

#[derive(Default)]
pub struct SignedTx {
    pub signatures: Vec<(usize, Vec<u8>)>,
    pub serialized: Vec<u8>,
}

impl Trezor {
    pub fn get_public_key(
        &mut self,
        path: &bip32::DerivationPath,
        network: Network,
        show_display: bool,
    ) -> Result<bip32::Xpub> {
        let mut req = protos::GetPublicKey::new();
        req.address_n = utils::convert_path(path);
        req.set_show_display(show_display);
        req.set_coin_name(utils::coin_name(network)?);
        self.call(req, Box::new(|_, m: protos::PublicKey| Ok(m.xpub().parse()?)))?.interact()
    }

    pub fn get_root_fingerprint(&mut self) -> Result<bip32::Fingerprint> {
        let xpub = self.get_public_key(
            &bip32::DerivationPath::default(),
            bitcoin::Network::Bitcoin,
            false,
        )?;
        Ok(xpub.fingerprint())
    }

    pub fn register_policy(
        &mut self,
        name: String,
        template: String,
        xpubs: Vec<String>,
        network: Network,
    ) -> Result<protos::RegisteredPolicy> {
        let mut req = protos::Policy::new();
        req.set_coin_name(utils::coin_name(network)?);
        req.set_name(name);
        req.set_template(template);
        req.xpubs = xpubs;
        self.call(req, Box::new(|_, m: protos::RegisteredPolicy| Ok(m)))?.interact()
    }

    //TODO(stevenroose) multisig
    pub fn get_address(
        &mut self,
        path: &bip32::DerivationPath,
        script_type: InputScriptType,
        network: Network,
        show_display: bool,
        registered: Option<protos::RegisteredPolicy>,
    ) -> Result<Address> {
        let mut req = protos::GetAddress::new();
        req.address_n = utils::convert_path(path);
        req.set_coin_name(utils::coin_name(network)?);
        req.set_show_display(show_display);
        req.set_script_type(script_type);
        req.registered = registered.into();
        self.call(req, Box::new(|_, m: protos::Address| parse_address(m.address())))?.interact()
    }

    pub fn sign_tx(
        &mut self,
        psbt: &psbt::Psbt,
        network: Network,
        registered: Option<protos::RegisteredPolicy>,
    ) -> Result<SignedTx> {
        let root_fingerprint = self.get_root_fingerprint()?;

        // Filter public keys that belong to the current wallet.
        // Public key derivation must be done before transaction signature process.
        let mut derivations = HashMap::new();
        for input in &psbt.inputs {
            for (pubkey, (fpr, path)) in &input.bip32_derivation {
                if *fpr != root_fingerprint {
                    continue;
                }
                let derived_pubkey = self.get_public_key(&path, network, false)?.public_key;
                if *pubkey == derived_pubkey {
                    if derivations.insert(derived_pubkey, path.clone()).is_some() {
                        return Err(crate::Error::InvalidPsbt(format!(
                            "Duplicate public key: {}",
                            derived_pubkey
                        )));
                    }
                }
            }
        }

        let tx = &psbt.unsigned_tx;
        let mut req = protos::SignTx::new();
        req.set_inputs_count(tx.input.len() as u32);
        req.set_outputs_count(tx.output.len() as u32);
        req.set_coin_name(utils::coin_name(network)?);
        req.set_version(tx.version.0 as u32);
        req.set_lock_time(tx.lock_time.to_consensus_u32());

        if registered.is_some() {
            // TODO: tx serialization is not fully supported with Miniscript
            req.serialize = Some(false);
        }

        let req = self.call(req, Box::new(move |_, m: protos::TxRequest| Ok(m)))?.interact()?;

        let mut progress =
            SignTxProgress::new(self, req, registered, root_fingerprint, derivations);
        let mut signed = SignedTx::default();
        loop {
            if let Some(part) = progress.get_serialized_tx_part() {
                signed.serialized.extend(part);
            }
            if let Some((i, sig)) = progress.get_signature() {
                signed.signatures.push((i, sig.to_vec()));
            }
            if progress.finished() {
                return Ok(signed);
            }
            progress.ack_psbt(psbt, network)?;
        }
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
