use heapless::Vec;
use trezor_thp::{
    channel::{PairingState, MAX_CREDENTIAL_LEN, MAX_DEVICE_PROPERTIES_LEN},
    credential::CredentialVerifier,
    noise::{Ciphers, NoiseHandshake, HANDSHAKE_HASH_LEN, PRIVKEY_LEN, PUBKEY_LEN, TAG_LEN},
    Error,
};

use crate::crypto::noise_xx::{Context, HandshakeContext};

// TODO: ZeroizeOnDrop
pub struct CipherState {
    ctx: Context,
    handshake_hash: [u8; HANDSHAKE_HASH_LEN],
    remote_static_pubkey: [u8; PUBKEY_LEN],
}

impl Ciphers for CipherState {
    fn encrypt(&mut self, in_out: &mut [u8], plaintext_len: usize) -> Result<(), Error> {
        let _ = self
            .ctx
            .send_message_inplace(&[], in_out, plaintext_len)
            .map_err(|_| Error::crypto_error())?;
        Ok(())
    }

    fn decrypt(&mut self, in_out: &mut [u8]) -> Result<usize, Error> {
        let len = self
            .ctx
            .receive_message_inplace(&[], in_out)
            .map_err(|_| Error::crypto_error())?;
        Ok(len)
    }

    fn handshake_hash(&self) -> &[u8; HANDSHAKE_HASH_LEN] {
        &self.handshake_hash
    }

    fn remote_static_pubkey(&self) -> &[u8; PUBKEY_LEN] {
        &self.remote_static_pubkey
    }
}

// TODO: ZeroizeOnDrop
pub struct Handshake {
    ctx: Option<HandshakeContext>,
    device_properties: Vec<u8, MAX_DEVICE_PROPERTIES_LEN>,
}

impl NoiseHandshake for Handshake {
    type Ciphers = CipherState;

    fn random_bytes(dest: &mut [u8]) {
        crate::trezorhal::random::bytes(dest);
    }

    fn prepare_responder(device_properties: &[u8]) -> Self {
        Self {
            ctx: None,
            device_properties: Vec::from_slice(device_properties).unwrap(),
        }
    }

    fn read_initiation_request(&mut self, receive_buffer: &[u8]) -> Result<bool, Error> {
        let (hctx, payload) =
            HandshakeContext::handle_initiation_request(&self.device_properties, receive_buffer)
                .map_err(|_| Error::crypto_error())?;
        let try_to_unlock = payload & 0x01 == 0x01;
        self.ctx = Some(hctx);
        Ok(try_to_unlock)
    }

    fn write_initiation_response(
        &mut self,
        static_privkey: &[u8; PRIVKEY_LEN],
        send_buffer: &mut [u8],
    ) -> Result<usize, Error> {
        let hctx = self.ctx.as_mut().ok_or_else(Error::unexpected_input)?;
        let response_size = hctx
            .create_initiation_response(static_privkey, send_buffer)
            .map_err(|_| Error::crypto_error())?;
        Ok(response_size)
    }

    fn write_completion_response(
        &mut self,
        receive_buffer: &[u8],
        cred_verifier: &impl CredentialVerifier,
        send_buffer: &mut [u8],
    ) -> Result<(Self::Ciphers, PairingState, usize), Error> {
        let mut payload = [0u8; MAX_CREDENTIAL_LEN];
        let hctx = self.ctx.as_mut().ok_or_else(Error::unexpected_input)?;
        let (cipher_ctx, payload_len) = hctx
            .handle_completion_request(receive_buffer, &mut payload)
            .map_err(|_| Error::crypto_error())?;

        let handshake_hash = *hctx.handshake_hash().ok_or_else(Error::crypto_error)?;
        let remote_static_pubkey = *hctx
            .remote_static_pubkey()
            .ok_or_else(Error::crypto_error)?;
        let mut ciphers = CipherState {
            ctx: cipher_ctx,
            handshake_hash,
            remote_static_pubkey,
        };
        let pairing_state =
            cred_verifier.verify(&ciphers.remote_static_pubkey, &payload[..payload_len]);

        let payload = &[pairing_state as u8];
        let plaintext_len = payload.len();
        let dest = send_buffer
            .get_mut(..plaintext_len + TAG_LEN)
            .ok_or_else(Error::insufficient_buffer)?;
        dest[0..plaintext_len].copy_from_slice(payload);
        ciphers.encrypt(dest, plaintext_len)?;
        Ok((ciphers, pairing_state, dest.len()))
    }

    #[cfg(feature = "test")]
    fn write_initiation_request(
        device_properties: &[u8],
        try_to_unlock: bool,
        dest: &mut [u8],
    ) -> Result<(Self, usize), Error> {
        let payload = u8::from(try_to_unlock);
        let (ctx, request_len) =
            HandshakeContext::create_initiation_request(device_properties, payload, dest)
                .map_err(|_| Error::crypto_error())?;
        let handshake = Self {
            ctx: Some(ctx),
            device_properties: Vec::new(),
        };
        Ok((handshake, request_len))
    }

    #[cfg(feature = "test")]
    fn write_completion_request(
        &mut self,
        cred_store: &mut impl trezor_thp::credential::CredentialStore,
        receive_buffer: &[u8],
        send_buffer: &mut [u8],
    ) -> Result<(Self::Ciphers, usize), Error> {
        let hctx = self.ctx.as_mut().ok_or_else(Error::unexpected_input)?;
        hctx.handle_initiation_response(receive_buffer)
            .map_err(|_| Error::crypto_error())?;

        // Look up static key based on remote keys, or generate a new one.
        let remote_static_pubkey = hctx
            .remote_static_pubkey()
            .ok_or_else(Error::crypto_error)?
            .clone();
        let remote_ephemeral_pubkey = hctx
            .remote_ephemeral_pubkey()
            .ok_or_else(Error::crypto_error)?;
        let (local_static, pairing_credential) =
            Self::credential_from_store(cred_store, remote_ephemeral_pubkey, &remote_static_pubkey);

        let (cipher_ctx, payload_len) = hctx
            .create_completion_request(&local_static, &pairing_credential, send_buffer)
            .map_err(|_| Error::crypto_error())?;
        let handshake_hash = hctx
            .handshake_hash()
            .ok_or_else(Error::crypto_error)?
            .clone();
        let mut ciphers = CipherState {
            ctx: cipher_ctx,
            handshake_hash,
            remote_static_pubkey,
        };
        Ok((ciphers, payload_len))
    }
}

#[cfg(feature = "test")]
impl Handshake {
    fn credential_from_store(
        cs: &impl trezor_thp::credential::CredentialStore,
        re: &[u8],
        rs: &[u8],
    ) -> ([u8; PRIVKEY_LEN], heapless::Vec<u8, MAX_CREDENTIAL_LEN>) {
        let mut buf = [0; { PRIVKEY_LEN + MAX_CREDENTIAL_LEN }];
        match cs.lookup(re, rs, &mut buf) {
            Some(found) => {
                let found_credential = heapless::Vec::from_slice(found.auth_credential).unwrap();
                (found.local_static_privkey.clone(), found_credential)
            }
            None => {
                let mut new_key = [0; PRIVKEY_LEN];
                Self::random_bytes(&mut new_key);
                (new_key, heapless::Vec::new())
            }
        }
    }
}
