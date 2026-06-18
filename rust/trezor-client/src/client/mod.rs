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

use crate::{
    error::{Error, Result},
    messages::TrezorMessage,
    protos,
    protos::MessageType::*,
    transport::{ProtoMessage, Transport},
    Model,
};
use protobuf::MessageField;
use tracing::{debug, trace};

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
    pub fn call<S: TrezorMessage, R: TrezorMessage>(&mut self, message: S) -> Result<R> {
        trace!("Sending {:?} msg: {:?}", S::MESSAGE_TYPE, message);
        let mut resp = self.call_raw(message)?;
        loop {
            if resp.message_type() == R::MESSAGE_TYPE {
                let resp_msg = resp.into_message()?;
                trace!("Received {:?} msg: {:?}", R::MESSAGE_TYPE, resp_msg);
                return Ok(resp_msg);
            }
            match resp.message_type() {
                MessageType_ButtonRequest => {
                    let req_msg: protos::ButtonRequest = resp.into_message()?;
                    trace!("Received ButtonRequest: {:?}", req_msg);
                    resp = self.call_raw(protos::ButtonAck::new())?;
                }
                MessageType_Failure => {
                    let fail_msg = resp.into_message()?;
                    debug!("Received failure: {:?}", fail_msg);
                    return Err(Error::FailureResponse(fail_msg));
                }
                mtype => {
                    debug!(
                        "Received unexpected msg type: {:?}; raw msg: {}",
                        mtype,
                        hex::encode(resp.into_payload())
                    );
                    return Err(Error::UnexpectedMessageType(mtype))
                }
            }
        }
    }

    pub fn init_device(&mut self, session_id: Option<Vec<u8>>) -> Result<()> {
        let features = self.initialize(session_id)?;
        self.features = Some(features);
        Ok(())
    }

    pub fn initialize(&mut self, session_id: Option<Vec<u8>>) -> Result<protos::Features> {
        let mut req = protos::Initialize::new();
        if let Some(session_id) = session_id {
            req.set_session_id(session_id);
        }
        self.call(req)
    }

    pub fn ping(&mut self, message: &str) -> Result<protos::Success> {
        let mut req = protos::Ping::new();
        req.set_message(message.to_owned());
        self.call(req)
    }

    pub fn change_pin(&mut self, remove: bool) -> Result<protos::Success> {
        let mut req = protos::ChangePin::new();
        req.set_remove(remove);
        self.call(req)
    }

    pub fn wipe_device(&mut self) -> Result<protos::Success> {
        let req = protos::WipeDevice::new();
        self.call(req)
    }

    pub fn recover_device(
        &mut self,
        word_count: u32,
        passphrase_protection: bool,
        pin_protection: bool,
        label: String,
        dry_run: bool,
    ) -> Result<protos::Success> {
        let mut req = protos::RecoveryDevice::new();
        req.set_word_count(word_count);
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
        self.call(req)
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
        external_entropy: Vec<u8>,
    ) -> Result<protos::Success> {
        if external_entropy.len() != 32 {
            return Err(Error::InvalidEntropy);
        }
        let mut req = protos::ResetDevice::new();
        req.set_strength(strength as u32);
        req.set_passphrase_protection(passphrase_protection);
        req.set_pin_protection(pin_protection);
        req.set_label(label);
        req.set_skip_backup(skip_backup);
        req.set_no_backup(no_backup);
        let _: protos::EntropyRequest = self.call(req)?;
        let mut ack = protos::EntropyAck::new();
        ack.set_entropy(external_entropy);
        self.call(ack)
    }

    pub fn backup(&mut self) -> Result<protos::Success> {
        let req = protos::BackupDevice::new();
        self.call(req)
    }

    //TODO(stevenroose) support U2F stuff? currently ignored all

    pub fn apply_settings(
        &mut self,
        label: Option<String>,
        use_passphrase: Option<bool>,
        homescreen: Option<Vec<u8>>,
        auto_lock_delay_ms: Option<usize>,
    ) -> Result<protos::Success> {
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
        self.call(req)
    }

    pub fn sign_identity(
        &mut self,
        identity: protos::IdentityType,
        digest: Vec<u8>,
        curve: String,
    ) -> Result<Vec<u8>> {
        let mut req = protos::SignIdentity::new();
        req.identity = MessageField::some(identity);
        req.set_challenge_hidden(digest);
        req.set_challenge_visual("".to_owned());
        req.set_ecdsa_curve_name(curve);
        let m: protos::SignedIdentity = self.call(req)?;
        Ok(m.signature().to_owned())
    }

    pub fn get_ecdh_session_key(
        &mut self,
        identity: protos::IdentityType,
        peer_public_key: Vec<u8>,
        curve: String,
    ) -> Result<protos::ECDHSessionKey> {
        let mut req = protos::GetECDHSessionKey::new();
        req.identity = MessageField::some(identity);
        req.set_peer_public_key(peer_public_key);
        req.set_ecdsa_curve_name(curve);
        self.call(req)
    }
}
