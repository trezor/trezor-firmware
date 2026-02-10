use trezor_noise_protocol::{
    Cipher, CipherState, DH, HandshakeState, Hash, U8Array, patterns::noise_xx,
};

use crate::{
    Device, Error, Host, Role,
    channel::PairingState,
    credential::{CREDENTIAL_PRIVKEY_LEN, CredentialStore, CredentialVerifier},
    util::prepare_zeroed,
};

use core::marker::PhantomData;

pub const HANDSHAKE_HASH_LEN: usize = 32;
pub const TAG_LEN: usize = 16;
pub const MAX_KEY_AND_CREDENTIAL_LEN: usize = 128;
const DH_PRIVKEY_LEN: usize = CREDENTIAL_PRIVKEY_LEN;

/// Cryptography backend trait.
///
/// Please see [`trezor-noise-rust-crypto` and `trezor-noise-ring`](http://github.com/trezor/noise-rust)
/// for implementations based on rust-crypto and ring.
pub trait Backend {
    /// Implementation of AES-256-GCM.
    type Cipher: Cipher;
    /// Implementation of X25519.
    type DH: DH;
    /// Implementation of SHA-256.
    type Hash: Hash;

    /// Fill entire destination with random bytes.
    fn random_bytes(dest: &mut [u8]);
}

type DHPrivKey<B> = <<B as Backend>::DH as DH>::Key;
type DHPubKey<B> = <<B as Backend>::DH as DH>::Pubkey;

pub struct NoiseHandshake<R: Role, B: Backend> {
    hss: HandshakeState<B::DH, B::Cipher, B::Hash>,
    _phantom: PhantomData<R>,
}
pub struct NoiseCiphers<B: Backend> {
    encrypt: CipherState<B::Cipher>,
    decrypt: CipherState<B::Cipher>,
    handshake_hash: [u8; HANDSHAKE_HASH_LEN],
}

impl<B: Backend> NoiseCiphers<B> {
    pub fn encrypt(&mut self, in_out: &mut [u8], plaintext_len: usize) -> Result<(), Error> {
        if in_out.len() < plaintext_len + TAG_LEN {
            return Err(Error::insufficient_buffer());
        }
        self.encrypt.encrypt_ad_in_place(&[], in_out, plaintext_len);
        Ok(())
    }

    pub fn decrypt(&mut self, in_out: &mut [u8]) -> Result<usize, Error> {
        if in_out.len() < TAG_LEN {
            return Err(Error::malformed_data());
        }
        self.decrypt
            .decrypt_ad_in_place(&[], in_out, in_out.len())
            .map_err(|()| Error::crypto_error())
    }

    pub fn handshake_hash(&self) -> &[u8; HANDSHAKE_HASH_LEN] {
        &self.handshake_hash
    }
}

impl<B: Backend> NoiseHandshake<Host, B> {
    pub fn initiation_request<'a>(
        device_properties: &[u8],
        try_to_unlock: bool,
        dest: &'a mut [u8],
    ) -> Result<(Self, &'a [u8]), Error> {
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
        let new = NoiseHandshake {
            hss,
            _phantom: PhantomData,
        };
        Ok((new, dest))
    }

    pub fn completion_request<'a>(
        &mut self,
        cred_store: &mut impl CredentialStore,
        buffer: &'a mut [u8],
        incoming_len: usize,
    ) -> Result<(NoiseCiphers<B>, &'a [u8]), Error> {
        if incoming_len != self.hss.get_next_message_overhead() {
            log::error!("Unexpected message length during handshake.");
            return Err(Error::malformed_data());
        }
        let incoming = buffer
            .get(..incoming_len)
            .ok_or_else(Error::insufficient_buffer)?;
        self.hss.read_message(incoming, &mut [])?;

        // Look up static key based on remote keys, or generate a new one.
        let remote_static_key = self.hss.get_rs().ok_or_else(Error::crypto_error)?;
        let remote_ephemeral_key = self.hss.get_re().ok_or_else(Error::crypto_error)?;
        let (local_static, pairing_credential) =
            Self::credential_from_store(cred_store, &remote_ephemeral_key, &remote_static_key)?;
        self.hss.set_s(local_static);

        buffer.fill(0);
        let len = self.hss.get_next_message_overhead() + pairing_credential.len();
        let dest = buffer
            .get_mut(..len)
            .ok_or_else(Error::insufficient_buffer)?;
        self.hss
            .write_message(pairing_credential.as_slice(), dest)?;
        if !self.hss.completed() {
            log::error!("Handshake not completed.");
            return Err(Error::crypto_error());
        }
        let (encrypt, decrypt) = self.hss.get_ciphers();
        let mut handshake_hash = [0u8; HANDSHAKE_HASH_LEN];
        handshake_hash.copy_from_slice(self.hss.get_hash());
        let nc = NoiseCiphers {
            encrypt,
            decrypt,
            handshake_hash,
        };
        Ok((nc, dest))
    }

    fn credential_from_store(
        cs: &impl CredentialStore,
        re: &DHPubKey<B>,
        rs: &DHPubKey<B>,
    ) -> Result<(DHPrivKey<B>, heapless::Vec<u8, MAX_KEY_AND_CREDENTIAL_LEN>), Error>
    where
        DHPrivKey<B>: U8Array,
    {
        let mut buf = heapless::Vec::new();
        prepare_zeroed(&mut buf);
        let result = cs.lookup(re.as_slice(), rs.as_slice(), buf.as_mut_slice());
        if let Some(found) = result {
            let found_key = <DHPrivKey<B> as U8Array>::from_slice(found.local_static_privkey);
            let found_credential = heapless::Vec::from_slice(found.auth_credential)
                .map_err(|_| Error::insufficient_buffer())?;
            return Ok((found_key, found_credential));
        }
        buf.clear();
        let new_key = <B::DH as DH>::genkey();
        Ok((new_key, buf))
    }
}

impl<B: Backend> NoiseHandshake<Device, B> {
    pub fn prepare_responder(
        static_privkey: &[u8; DH_PRIVKEY_LEN],
        device_properties: &[u8],
    ) -> Self {
        let mk = Self::mask_key(static_privkey);
        let mut hss = HandshakeState::new(
            noise_xx(),
            /*is_initiator=*/ false,
            /*prologue=*/ device_properties,
            /*s=*/ Some(mk.static_privkey),
            /*e=*/ Some(mk.ephemeral_privkey),
            /*re=*/ None,
            /*rs=*/ None,
        );
        hss.set_s_mask(mk.mask);
        NoiseHandshake {
            hss,
            _phantom: PhantomData,
        }
    }

    pub fn initiation_response<'a>(
        &mut self,
        incoming: &[u8],
        dest: &'a mut [u8],
    ) -> Result<(bool, &'a [u8]), Error> {
        const PAYLOAD_LEN: usize = 1;
        if incoming.len() != self.hss.get_next_message_overhead() + PAYLOAD_LEN {
            log::error!("Unexpected message length during handshake.");
            return Err(Error::malformed_data());
        }
        let mut payload = [0u8; PAYLOAD_LEN];
        self.hss.read_message(incoming, &mut payload)?;
        let try_to_unlock = u8_to_bool(payload[0])?;
        let len = self.hss.get_next_message_overhead();
        let dest = dest.get_mut(..len).ok_or_else(Error::insufficient_buffer)?;
        self.hss.write_message(/*payload*/ &[], dest)?; // no outgoing payload
        Ok((try_to_unlock, dest))
    }

    pub fn completion_response<'a>(
        &mut self,
        incoming: &[u8],
        cred_verifier: &impl CredentialVerifier,
        dest: &'a mut [u8],
    ) -> Result<(NoiseCiphers<B>, PairingState, &'a [u8]), Error> {
        let overhead_len = self.hss.get_next_message_overhead();
        if incoming.len() < overhead_len {
            log::error!("Unexpected message length during handshake.");
            return Err(Error::malformed_data());
        }
        let cred_len = incoming.len().saturating_sub(overhead_len);
        let mut cred = heapless::Vec::<u8, MAX_KEY_AND_CREDENTIAL_LEN>::new();
        cred.resize(cred_len, 0u8)
            .map_err(|_| Error::insufficient_buffer())?;
        self.hss.read_message(incoming, &mut cred)?;
        if !self.hss.completed() {
            log::error!("Handshake not completed.");
            return Err(Error::crypto_error());
        }

        let remote_static_pubkey = self.hss.get_rs().ok_or_else(Error::crypto_error)?;
        let (decrypt, encrypt) = self.hss.get_ciphers();
        let mut handshake_hash = [0u8; HANDSHAKE_HASH_LEN];
        handshake_hash.copy_from_slice(self.hss.get_hash());
        let mut nc = NoiseCiphers {
            encrypt,
            decrypt,
            handshake_hash,
        };
        let pairing_state = cred_verifier.verify(remote_static_pubkey.as_slice(), &cred);
        let payload = &[pairing_state as u8];
        let plaintext_len = payload.len();
        let dest = dest
            .get_mut(..plaintext_len + TAG_LEN)
            .ok_or_else(Error::insufficient_buffer)?;
        dest[0..plaintext_len].copy_from_slice(payload);
        nc.encrypt(dest, plaintext_len)?;
        Ok((nc, pairing_state, dest))
    }

    fn mask_key(static_privkey: &[u8; DH_PRIVKEY_LEN]) -> MaskKeyResult<B>
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

struct MaskKeyResult<B: Backend> {
    static_privkey: DHPrivKey<B>,
    ephemeral_privkey: DHPrivKey<B>,
    mask: DHPrivKey<B>,
}

fn hash_of_two<B: Backend>(in1: &[u8], in2: &[u8]) -> [u8; DH_PRIVKEY_LEN] {
    let mut res = [0u8; DH_PRIVKEY_LEN];
    let mut h = <B::Hash as Default>::default();
    h.input(in1);
    h.input(in2);
    res.copy_from_slice(h.result().as_slice());
    res
}

fn u8_to_bool(val: u8) -> Result<bool, Error> {
    match val {
        0u8 => Ok(false),
        1u8 => Ok(true),
        _ => {
            log::error!("Invalid try_to_unlock value: {}.", val);
            Err(Error::malformed_data())
        }
    }
}
