use trezor_noise_protocol::{CipherState, HandshakeState, patterns::noise_xx};

pub use trezor_noise_protocol::{Cipher, DH, Hash, U8Array};

use crate::{
    Error,
    channel::{MAX_CREDENTIAL_LEN, PairingState},
    credential::{CredentialStore, CredentialVerifier},
    util::prepare_zeroed,
};

use super::{Ciphers, HANDSHAKE_HASH_LEN, NoiseHandshake, PRIVKEY_LEN, PUBKEY_LEN, TAG_LEN};

/// Cryptography backend trait.
///
/// Please see [`trezor-noise-rust-crypto` and `trezor-noise-ring`](http://github.com/trezor/noise-rust)
/// for implementations based on rust-crypto and ring.
pub trait TrezorNoiseProtocolBackend {
    /// Implementation of AES-256-GCM.
    type Cipher: Cipher;
    /// Implementation of X25519.
    type DH: DH;
    /// Implementation of SHA-256.
    type Hash: Hash;

    /// Fill entire destination with random bytes.
    fn random_bytes(dest: &mut [u8]);
}

type DHPrivKey<B> = <<B as TrezorNoiseProtocolBackend>::DH as DH>::Key;
type DHPubKey<B> = <<B as TrezorNoiseProtocolBackend>::DH as DH>::Pubkey;

pub struct TrezorNoiseProtocol<B: TrezorNoiseProtocolBackend> {
    hss: HandshakeState<B::DH, B::Cipher, B::Hash>,
}

pub struct NoiseCiphers<B: TrezorNoiseProtocolBackend> {
    encrypt: CipherState<B::Cipher>,
    decrypt: CipherState<B::Cipher>,
    handshake_hash: [u8; HANDSHAKE_HASH_LEN],
    remote_static_pubkey: [u8; PUBKEY_LEN],
}

impl<B: TrezorNoiseProtocolBackend> Ciphers for NoiseCiphers<B> {
    fn encrypt(&mut self, in_out: &mut [u8], plaintext_len: usize) -> Result<(), Error> {
        if in_out.len() < plaintext_len + TAG_LEN {
            return Err(Error::insufficient_buffer());
        }
        self.encrypt.encrypt_ad_in_place(&[], in_out, plaintext_len);
        Ok(())
    }

    fn decrypt(&mut self, in_out: &mut [u8]) -> Result<usize, Error> {
        if in_out.len() < TAG_LEN {
            return Err(Error::malformed_data());
        }
        self.decrypt
            .decrypt_ad_in_place(&[], in_out, in_out.len())
            .map_err(|()| Error::crypto_error())
    }

    fn handshake_hash(&self) -> &[u8; HANDSHAKE_HASH_LEN] {
        &self.handshake_hash
    }

    fn remote_static_pubkey(&self) -> &[u8; PUBKEY_LEN] {
        &self.remote_static_pubkey
    }
}

impl<B: TrezorNoiseProtocolBackend> NoiseHandshake for TrezorNoiseProtocol<B> {
    type Ciphers = NoiseCiphers<B>;

    fn random_bytes(dest: &mut [u8]) {
        B::random_bytes(dest);
    }

    fn write_initiation_request(
        device_properties: &[u8],
        try_to_unlock: bool,
        dest: &mut [u8],
    ) -> Result<(Self, usize), Error> {
        let payload = &[u8::from(try_to_unlock)];
        let mut hss = HandshakeState::new(
            noise_xx(),
            /*is_initiator=*/ true,
            /*prologue=*/ device_properties,
            /*s=*/ None, // will be set later based on cred_lookup
            /*e=*/ None, // random
            /*re=*/ None,
            /*rs=*/ None,
        );
        let len = hss.get_next_message_overhead() + payload.len();
        let dest = dest.get_mut(..len).ok_or_else(Error::insufficient_buffer)?;
        hss.write_message(payload, dest)?;
        let new = TrezorNoiseProtocol { hss };
        Ok((new, len))
    }

    fn write_completion_request(
        &mut self,
        cred_store: &mut impl CredentialStore,
        receive_buffer: &[u8],
        send_buffer: &mut [u8],
    ) -> Result<(NoiseCiphers<B>, usize), Error> {
        if receive_buffer.len() != self.hss.get_next_message_overhead() {
            log::error!("Unexpected message length during handshake.");
            return Err(Error::malformed_data());
        }
        self.hss.read_message(receive_buffer, &mut [])?;

        // Look up static key based on remote keys, or generate a new one.
        let remote_static_pubkey = self.hss.get_rs().ok_or_else(Error::crypto_error)?;
        let remote_ephemeral_pubkey = self.hss.get_re().ok_or_else(Error::crypto_error)?;
        let (local_static, pairing_credential) = Self::credential_from_store(
            cred_store,
            &remote_ephemeral_pubkey,
            &remote_static_pubkey,
        )?;
        self.hss.set_s(local_static);

        send_buffer.fill(0);
        let len = self.hss.get_next_message_overhead() + pairing_credential.len();
        let dest = send_buffer
            .get_mut(..len)
            .ok_or_else(Error::insufficient_buffer)?;
        self.hss
            .write_message(pairing_credential.as_slice(), dest)?;
        if !self.hss.completed() {
            log::error!("Handshake not completed.");
            return Err(Error::crypto_error());
        }
        let (encrypt, decrypt) = self.hss.get_ciphers();
        let handshake_hash = self.hss.get_hash().try_into().unwrap();
        let nc = NoiseCiphers {
            encrypt,
            decrypt,
            handshake_hash,
            remote_static_pubkey: remote_static_pubkey.as_slice().try_into().unwrap(),
        };
        Ok((nc, len))
    }

    fn prepare_responder(device_properties: &[u8]) -> Self {
        let hss = HandshakeState::new(
            noise_xx(),
            /*is_initiator=*/ false,
            /*prologue=*/ device_properties,
            /*s=*/ None,
            /*e=*/ None,
            /*re=*/ None,
            /*rs=*/ None,
        );
        TrezorNoiseProtocol { hss }
    }

    fn read_initiation_request(&mut self, incoming: &[u8]) -> Result<bool, Error> {
        const PAYLOAD_LEN: usize = 1;
        if incoming.len() != self.hss.get_next_message_overhead() + PAYLOAD_LEN {
            log::error!("Unexpected message length during handshake.");
            return Err(Error::malformed_data());
        }
        let mut payload = [0u8; PAYLOAD_LEN];
        self.hss.read_message(incoming, &mut payload)?;
        let try_to_unlock = payload[0] & 0x01 == 0x01;
        Ok(try_to_unlock)
    }

    fn write_initiation_response(
        &mut self,
        static_privkey: &[u8; PRIVKEY_LEN],
        dest: &mut [u8],
    ) -> Result<usize, Error> {
        let mk = Self::mask_key(static_privkey);
        self.hss.set_s(mk.static_privkey);
        self.hss.set_s_mask(mk.mask);
        self.hss.set_e(mk.ephemeral_privkey);
        let len = self.hss.get_next_message_overhead();
        let dest = dest.get_mut(..len).ok_or_else(Error::insufficient_buffer)?;
        self.hss.write_message(/*payload*/ &[], dest)?; // no outgoing payload
        Ok(len)
    }

    fn write_completion_response(
        &mut self,
        incoming: &[u8],
        cred_verifier: &impl CredentialVerifier,
        dest: &mut [u8],
    ) -> Result<(NoiseCiphers<B>, PairingState, usize), Error> {
        let overhead_len = self.hss.get_next_message_overhead();
        if incoming.len() < overhead_len {
            log::error!("Unexpected message length during handshake.");
            return Err(Error::malformed_data());
        }
        let cred_len = incoming.len().saturating_sub(overhead_len);
        let mut cred = heapless::Vec::<u8, MAX_CREDENTIAL_LEN>::new();
        cred.resize(cred_len, 0u8)
            .map_err(|_| Error::insufficient_buffer())?;
        self.hss.read_message(incoming, &mut cred)?;
        if !self.hss.completed() {
            log::error!("Handshake not completed.");
            return Err(Error::crypto_error());
        }

        let remote_static_pubkey = self
            .hss
            .get_rs()
            .ok_or_else(Error::crypto_error)?
            .as_slice()
            .try_into()
            .unwrap();
        let handshake_hash = self.hss.get_hash().try_into().unwrap();
        let (decrypt, encrypt) = self.hss.get_ciphers();
        let mut nc = NoiseCiphers {
            encrypt,
            decrypt,
            handshake_hash,
            remote_static_pubkey,
        };
        let pairing_state = cred_verifier.verify(&nc.remote_static_pubkey, &cred);
        let payload = &[pairing_state as u8];
        let plaintext_len = payload.len();
        let dest = dest
            .get_mut(..plaintext_len + TAG_LEN)
            .ok_or_else(Error::insufficient_buffer)?;
        dest[0..plaintext_len].copy_from_slice(payload);
        nc.encrypt(dest, plaintext_len)?;
        Ok((nc, pairing_state, dest.len()))
    }
}

impl<B: TrezorNoiseProtocolBackend> TrezorNoiseProtocol<B> {
    fn credential_from_store(
        cs: &impl CredentialStore,
        re: &DHPubKey<B>,
        rs: &DHPubKey<B>,
    ) -> Result<(DHPrivKey<B>, heapless::Vec<u8, MAX_CREDENTIAL_LEN>), Error>
    where
        DHPrivKey<B>: U8Array,
    {
        let mut buf = heapless::Vec::<u8, { PRIVKEY_LEN + MAX_CREDENTIAL_LEN }>::new();
        prepare_zeroed(&mut buf);
        let result = cs.lookup(re.as_slice(), rs.as_slice(), buf.as_mut_slice());
        if let Some(found) = result {
            let found_key = <DHPrivKey<B> as U8Array>::from_slice(found.local_static_privkey);
            let found_credential = heapless::Vec::from_slice(found.auth_credential)
                .map_err(|_| Error::insufficient_buffer())?;
            return Ok((found_key, found_credential));
        }
        let new_key = <B::DH as DH>::genkey();
        Ok((new_key, heapless::Vec::new()))
    }
}

impl<B: TrezorNoiseProtocolBackend> TrezorNoiseProtocol<B> {
    fn mask_key(static_privkey: &[u8; PRIVKEY_LEN]) -> MaskKeyResult<B>
    where
        DHPrivKey<B>: U8Array,
    {
        let static_privkey = <DHPrivKey<B> as U8Array>::from_slice(static_privkey);
        let static_pubkey = <B::DH as DH>::pubkey(&static_privkey);
        let ephemeral_privkey = <B::DH as DH>::genkey();
        let ephemeral_pubkey = <B::DH as DH>::pubkey(&ephemeral_privkey);
        let mask = hash_of_two::<B>(static_pubkey.as_slice(), ephemeral_pubkey.as_slice());
        let mask = <DHPrivKey<B> as U8Array>::from_slice(&mask);
        MaskKeyResult {
            static_privkey,
            ephemeral_privkey,
            mask,
        }
    }
}

struct MaskKeyResult<B: TrezorNoiseProtocolBackend> {
    static_privkey: DHPrivKey<B>,
    ephemeral_privkey: DHPrivKey<B>,
    mask: DHPrivKey<B>,
}

fn hash_of_two<B: TrezorNoiseProtocolBackend>(in1: &[u8], in2: &[u8]) -> [u8; PRIVKEY_LEN] {
    let mut res = [0u8; PRIVKEY_LEN];
    let mut h = <B::Hash as Default>::default();
    h.input(in1);
    h.input(in2);
    res.copy_from_slice(h.result().as_slice());
    res
}
