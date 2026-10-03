#[cfg(feature = "bitcoin")]
mod bitcoin;
#[cfg(feature = "bitcoin")]
pub use self::bitcoin::*;

#[cfg(feature = "ethereum")]
mod ethereum;
#[cfg(feature = "ethereum")]
pub use ethereum::*;

#[cfg(feature = "solana")]
mod solana;

pub mod common;
pub use common::*;

use crate::{
    error::{Error, Result},
    messages::TrezorMessage,
    protos,
    protos::MessageType::*,
    transport::{ProtoMessage, Transport},
    Model,
};
use protobuf::{MessageField, MessageFull};
use tracing::{debug, trace};

/// Message fields whose contents must never be written to a log, keyed by the
/// protobuf message's full name and the field name within it.
///
/// The selection criterion is "a secret or an authentication credential
/// carried by an exchange this crate performs". `ECDHSessionKey.session_key`
/// is the shared decryption secret; `PinMatrixAck.pin` and
/// `PassphraseAck.passphrase` are the user credentials being sent to the
/// device; and `SignedIdentity.signature` is authentication material that
/// should not be persisted to logs. The list is deliberately scoped to the
/// fields the crate's typed helpers actually exchange, and is trivial to
/// extend if more such methods are added.
const REDACTED_FIELDS: &[(&str, &str)] = &[
    ("hw.trezor.messages.crypto.SignedIdentity", "signature"),
    ("hw.trezor.messages.crypto.ECDHSessionKey", "session_key"),
    ("hw.trezor.messages.common.PinMatrixAck", "pin"),
    ("hw.trezor.messages.common.PassphraseAck", "passphrase"),
];

/// Formats `msg` for logging with any [`REDACTED_FIELDS`] cleared, so a secret
/// cannot be emitted through the crate's tracing. Messages that carry no
/// redacted field are formatted exactly like their derived `Debug`.
///
/// Redaction is applied here, at the crate's own device-I/O log call sites
/// (the only place these messages are logged); it does not replace `Debug` on
/// the generated types. The `trace!` macro only evaluates this when a
/// subscriber has enabled the call site, so callers that do not log pay
/// nothing.
fn redacted_debug<M: MessageFull>(msg: &M) -> String {
    let descriptor = M::descriptor();
    let full_name = descriptor.full_name();
    let redacted: Vec<_> = descriptor
        .fields()
        .filter(|field| {
            REDACTED_FIELDS
                .iter()
                .any(|(message, name)| *message == full_name && *name == field.name())
        })
        .collect();
    if redacted.is_empty() {
        return format!("{msg:?}");
    }

    let mut clone = msg.clone();
    for field in &redacted {
        field.clear_field(&mut clone);
    }
    let names: Vec<&str> = redacted.iter().map(|field| field.name()).collect();
    format!("{clone:?} [redacted: {}]", names.join(", "))
}

/// A Trezor client.
pub struct Trezor {
    model: Model,
    // Cached features for later inspection.
    features: Option<protos::Features>,
    transport: Box<dyn Transport>,
}

/// Create a new Trezor instance with the given transport.
pub fn trezor_with_transport(model: Model, transport: Box<dyn Transport>) -> Trezor {
    Trezor { model, transport, features: None }
}

impl Trezor {
    /// Get the model of the Trezor device.
    pub fn model(&self) -> Model {
        self.model
    }

    /// Get the features of the Trezor device.
    pub fn features(&self) -> Option<&protos::Features> {
        self.features.as_ref()
    }

    /// Sends a message and returns the raw ProtoMessage struct that was responded by the device.
    /// This method is only exported for users that want to expand the features of this library
    /// f.e. for supporting additional coins etc.
    pub fn call_raw<S: TrezorMessage>(&mut self, message: S) -> Result<ProtoMessage> {
        let proto_msg = ProtoMessage(S::MESSAGE_TYPE, message.write_to_bytes()?);
        self.transport.write_message(proto_msg).map_err(Error::TransportSendMessage)?;
        self.transport.read_message().map_err(Error::TransportReceiveMessage)
    }

    /// Sends a message without waiting for a response.
    /// Useful for fire-and-forget debug messages such as `DebugLinkDecision`, which the
    /// firmware may not reply to.
    pub fn send_message<S: TrezorMessage>(&mut self, message: S) -> Result<()> {
        let proto_msg = ProtoMessage(S::MESSAGE_TYPE, message.write_to_bytes()?);
        self.transport.write_message(proto_msg).map_err(Error::TransportSendMessage)
    }

    /// Sends a message and returns a TrezorResponse with either the expected response message,
    /// a failure or an interaction request.
    /// This method is only exported for users that want to expand the features of this library
    /// f.e. for supporting additional coins etc.
    pub fn call<'a, T, S: TrezorMessage, R: TrezorMessage>(
        &'a mut self,
        message: S,
        result_handler: Box<ResultHandler<'a, T, R>>,
    ) -> Result<TrezorResponse<'a, T, R>> {
        trace!("Sending {:?} msg: {}", S::MESSAGE_TYPE, redacted_debug(&message));
        let resp = self.call_raw(message)?;
        if resp.message_type() == R::MESSAGE_TYPE {
            let resp_msg = resp.into_message()?;
            trace!("Received {:?} msg: {}", R::MESSAGE_TYPE, redacted_debug(&resp_msg));
            Ok(TrezorResponse::Ok(result_handler(self, resp_msg)?))
        } else {
            match resp.message_type() {
                MessageType_Failure => {
                    let fail_msg = resp.into_message()?;
                    debug!("Received failure: {:?}", fail_msg);
                    Ok(TrezorResponse::Failure(fail_msg))
                }
                MessageType_ButtonRequest => {
                    let req_msg = resp.into_message()?;
                    trace!("Received ButtonRequest: {:?}", req_msg);
                    Ok(TrezorResponse::ButtonRequest(ButtonRequest {
                        message: req_msg,
                        client: self,
                        result_handler,
                    }))
                }
                MessageType_PinMatrixRequest => {
                    let req_msg = resp.into_message()?;
                    trace!("Received PinMatrixRequest: {:?}", req_msg);
                    Ok(TrezorResponse::PinMatrixRequest(PinMatrixRequest {
                        message: req_msg,
                        client: self,
                        result_handler,
                    }))
                }
                MessageType_PassphraseRequest => {
                    let req_msg = resp.into_message()?;
                    trace!("Received PassphraseRequest: {:?}", req_msg);
                    Ok(TrezorResponse::PassphraseRequest(PassphraseRequest {
                        message: req_msg,
                        client: self,
                        result_handler,
                    }))
                }
                mtype => {
                    debug!(
                        "Received unexpected msg type: {:?}; raw msg: {}",
                        mtype,
                        hex::encode(resp.into_payload())
                    );
                    Err(Error::UnexpectedMessageType(mtype))
                }
            }
        }
    }

    pub fn init_device(&mut self, session_id: Option<Vec<u8>>) -> Result<()> {
        let features = self.initialize(session_id)?.ok()?;
        self.features = Some(features);
        Ok(())
    }

    pub fn initialize(
        &mut self,
        session_id: Option<Vec<u8>>,
    ) -> Result<TrezorResponse<'_, Features, Features>> {
        let mut req = protos::Initialize::new();
        if let Some(session_id) = session_id {
            req.set_session_id(session_id);
        }
        self.call(req, Box::new(|_, m| Ok(m)))
    }

    pub fn ping(&mut self, message: &str) -> Result<TrezorResponse<'_, (), protos::Success>> {
        let mut req = protos::Ping::new();
        req.set_message(message.to_owned());
        self.call(req, Box::new(|_, _| Ok(())))
    }

    pub fn change_pin(&mut self, remove: bool) -> Result<TrezorResponse<'_, (), protos::Success>> {
        let mut req = protos::ChangePin::new();
        req.set_remove(remove);
        self.call(req, Box::new(|_, _| Ok(())))
    }

    pub fn wipe_device(&mut self) -> Result<TrezorResponse<'_, (), protos::Success>> {
        let req = protos::WipeDevice::new();
        self.call(req, Box::new(|_, _| Ok(())))
    }

    pub fn recover_device(
        &mut self,
        word_count: WordCount,
        passphrase_protection: bool,
        pin_protection: bool,
        label: String,
        dry_run: bool,
    ) -> Result<TrezorResponse<'_, (), protos::Success>> {
        let mut req = protos::RecoveryDevice::new();
        req.set_word_count(word_count as u32);
        req.set_passphrase_protection(passphrase_protection);
        req.set_pin_protection(pin_protection);
        req.set_label(label);
        req.set_enforce_wordlist(true);
        if dry_run {
            req.set_type(protos::RecoveryType::DryRun);
        } else {
            req.set_type(protos::RecoveryType::NormalRecovery);
        }
        req.set_input_method(protos::recovery_device::RecoveryDeviceInputMethod::ScrambledWords);
        //TODO(stevenroose) support languages
        req.set_language("english".to_owned());
        self.call(req, Box::new(|_, _| Ok(())))
    }

    #[allow(clippy::too_many_arguments)]
    pub fn reset_device(
        &mut self,
        strength: usize,
        passphrase_protection: bool,
        pin_protection: bool,
        label: String,
        skip_backup: bool,
        no_backup: bool,
    ) -> Result<TrezorResponse<'_, EntropyRequest<'_>, protos::EntropyRequest>> {
        let mut req = protos::ResetDevice::new();
        req.set_strength(strength as u32);
        req.set_passphrase_protection(passphrase_protection);
        req.set_pin_protection(pin_protection);
        req.set_label(label);
        req.set_skip_backup(skip_backup);
        req.set_no_backup(no_backup);
        self.call(req, Box::new(|c, _| Ok(EntropyRequest { client: c })))
    }

    pub fn backup(&mut self) -> Result<TrezorResponse<'_, (), protos::Success>> {
        let req = protos::BackupDevice::new();
        self.call(req, Box::new(|_, _| Ok(())))
    }

    //TODO(stevenroose) support U2F stuff? currently ignored all

    pub fn apply_settings(
        &mut self,
        label: Option<String>,
        use_passphrase: Option<bool>,
        homescreen: Option<Vec<u8>>,
        auto_lock_delay_ms: Option<usize>,
    ) -> Result<TrezorResponse<'_, (), protos::Success>> {
        let mut req = protos::ApplySettings::new();
        if let Some(label) = label {
            req.set_label(label);
        }
        if let Some(use_passphrase) = use_passphrase {
            req.set_use_passphrase(use_passphrase);
        }
        if let Some(homescreen) = homescreen {
            req.set_homescreen(homescreen);
        }
        if let Some(auto_lock_delay_ms) = auto_lock_delay_ms {
            req.set_auto_lock_delay_ms(auto_lock_delay_ms as u32);
        }
        self.call(req, Box::new(|_, _| Ok(())))
    }

    pub fn sign_identity(
        &mut self,
        identity: protos::IdentityType,
        digest: Vec<u8>,
        curve: String,
    ) -> Result<TrezorResponse<'_, Vec<u8>, protos::SignedIdentity>> {
        let mut req = protos::SignIdentity::new();
        req.identity = MessageField::some(identity);
        req.set_challenge_hidden(digest);
        req.set_challenge_visual("".to_owned());
        req.set_ecdsa_curve_name(curve);
        self.call(req, Box::new(|_, m| Ok(m.signature().to_owned())))
    }

    pub fn get_ecdh_session_key(
        &mut self,
        identity: protos::IdentityType,
        peer_public_key: Vec<u8>,
        curve: String,
    ) -> Result<TrezorResponse<'_, protos::ECDHSessionKey, protos::ECDHSessionKey>> {
        let mut req = protos::GetECDHSessionKey::new();
        req.identity = MessageField::some(identity);
        req.set_peer_public_key(peer_public_key);
        req.set_ecdsa_curve_name(curve);
        self.call(req, Box::new(|_, m| Ok(m)))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn redacts_signed_identity_signature() {
        let mut msg = protos::SignedIdentity::new();
        msg.set_public_key(vec![0x01, 0x02, 0x03]);
        msg.set_signature(vec![0xab; 8]);

        let out = redacted_debug(&msg);
        // The secret signature bytes (171 == 0xab in the `Debug` of a
        // `Vec<u8>`) must not appear, and the field must read as cleared.
        assert!(!out.contains("171"), "signature leaked: {out}");
        assert!(out.contains("signature: None"), "signature not cleared: {out}");
        // Non-secret context and the redaction marker remain.
        assert!(out.contains("public_key"), "lost useful context: {out}");
        assert!(out.contains("[redacted: signature]"), "no redaction marker: {out}");
    }

    #[test]
    fn redacts_ecdh_session_key() {
        let mut msg = protos::ECDHSessionKey::new();
        msg.set_public_key(vec![0x01, 0x02, 0x03]);
        msg.set_session_key(vec![0xcd; 8]);

        let out = redacted_debug(&msg);
        assert!(!out.contains("205"), "session key leaked: {out}");
        assert!(out.contains("session_key: None"), "session key not cleared: {out}");
        assert!(out.contains("[redacted: session_key]"), "no redaction marker: {out}");
    }

    #[test]
    fn redacts_credentials_sent_to_device() {
        let mut pin = protos::PinMatrixAck::new();
        pin.set_pin("997531".to_owned());
        let out = redacted_debug(&pin);
        assert!(!out.contains("997531"), "pin leaked: {out}");
        assert!(out.contains("[redacted: pin]"), "no redaction marker: {out}");

        let mut passphrase = protos::PassphraseAck::new();
        passphrase.set_passphrase("hunter2".to_owned());
        let out = redacted_debug(&passphrase);
        assert!(!out.contains("hunter2"), "passphrase leaked: {out}");
        assert!(out.contains("[redacted: passphrase]"), "no redaction marker: {out}");
    }

    #[test]
    fn leaves_non_secret_messages_unchanged() {
        let mut msg = protos::Features::new();
        msg.set_vendor("trezor.io".to_owned());
        // A message with no redacted field formats exactly like its `Debug`.
        assert_eq!(redacted_debug(&msg), format!("{msg:?}"));
    }
}
