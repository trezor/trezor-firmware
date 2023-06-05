use super::{Trezor, TrezorResponse};
use crate::{error::Result, flows::sign_tx::SignTxProgress, protos, utils};
use bitcoin::{
    address::NetworkUnchecked, bip32, network::constants::Network, psbt,
    secp256k1::ecdsa::RecoverableSignature, Address,
};

pub use crate::protos::InputScriptType;

impl Trezor {
    pub fn get_public_key(
        &mut self,
        path: &bip32::DerivationPath,
        script_type: InputScriptType,
        network: Network,
        show_display: bool,
    ) -> Result<TrezorResponse<'_, bip32::ExtendedPubKey, protos::PublicKey>> {
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

    pub fn sign_tx(
        &mut self,
        psbt: &psbt::PartiallySignedTransaction,
        network: Network,
    ) -> Result<TrezorResponse<'_, SignTxProgress<'_>, protos::TxRequest>> {
        let tx = &psbt.unsigned_tx;
        let mut req = protos::SignTx::new();
        req.set_inputs_count(tx.input.len() as u32);
        req.set_outputs_count(tx.output.len() as u32);
        req.set_coin_name(utils::coin_name(network)?);
        req.set_version(tx.version as u32);
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
