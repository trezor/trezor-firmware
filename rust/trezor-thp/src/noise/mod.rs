//! Traits for the Noise XX patern. See https://noiseprotocol.org/
//! Host is the initiator, device is the responder.
//!
//!  -> e               # initiation request
//!  <- e, ee, s, es    # initiation response
//!  -> s, se           # completion request
//!  <- (pairing_state) # completion response - technically not part of the handshake as secure channel is established at this point

#[cfg(feature = "trezor_noise_protocol")]
pub mod forked;

#[cfg(feature = "noise_protocol")]
pub mod noise_protocol;

use crate::{
    Error,
    channel::PairingState,
    credential::{CredentialStore, CredentialVerifier},
};

pub const HANDSHAKE_HASH_LEN: usize = 32;
pub const PRIVKEY_LEN: usize = 32;
pub const PUBKEY_LEN: usize = 32;
pub const TAG_LEN: usize = 16;

pub trait Ciphers {
    fn encrypt(&mut self, in_out: &mut [u8], plaintext_len: usize) -> Result<(), Error>;
    fn decrypt(&mut self, in_out: &mut [u8]) -> Result<usize, Error>;
    fn handshake_hash(&self) -> &[u8; HANDSHAKE_HASH_LEN];
    fn remote_static_pubkey(&self) -> &[u8; PUBKEY_LEN];
}

pub trait NoiseHandshake: Sized {
    type Ciphers: Ciphers;

    /// Fill entire destination with random bytes.
    fn random_bytes(dest: &mut [u8]);

    // Host/initiator needs to implement the following methods:
    fn write_initiation_request(
        _device_properties: &[u8],
        _try_to_unlock: bool,
        _dest: &mut [u8],
    ) -> Result<(Self, usize), Error> {
        unimplemented!("This backend does not implement the host side handshake.");
    }
    fn write_completion_request(
        &mut self,
        _cred_store: &mut impl CredentialStore,
        _receive_buffer: &[u8],
        _send_buffer: &mut [u8],
    ) -> Result<(Self::Ciphers, usize), Error> {
        unimplemented!("This backend does not implement the host side handshake.");
    }

    // Device/responder needs to implement the following methods:
    fn prepare_responder(_device_properties: &[u8]) -> Self {
        unimplemented!("This backend does not implement device side handshake.");
    }
    fn read_initiation_request(&mut self, _receive_buffer: &[u8]) -> Result<bool, Error> {
        unimplemented!("This backend does not implement device side handshake.");
    }
    fn write_initiation_response(
        &mut self,
        _static_privkey: &[u8; PRIVKEY_LEN],
        _send_buffer: &mut [u8],
    ) -> Result<usize, Error> {
        unimplemented!("This backend does not implement device side handshake.");
    }
    fn write_completion_response(
        &mut self,
        _receive_buffer: &[u8],
        _cred_verifier: &impl CredentialVerifier,
        _send_buffer: &mut [u8],
    ) -> Result<(Self::Ciphers, PairingState, usize), Error> {
        unimplemented!("This backend does not implement device side handshake.");
    }
}
