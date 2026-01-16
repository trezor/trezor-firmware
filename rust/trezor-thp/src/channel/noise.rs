use trezor_noise_protocol::{
    Cipher, CipherState, DH, HandshakeState, Hash, U8Array, patterns::noise_xx,
};

use crate::{Error, Host, Role, credential::CredentialStore};

use core::marker::PhantomData;

pub const HANDSHAKE_HASH_LEN: usize = 32;
pub const TAG_LEN: usize = 16;
pub const MAX_KEY_AND_CREDENTIAL_LEN: usize = 128;

/// Cryptography backend trait.
///
/// Please see [`trezor-noise-rust-crypto` and `trezor-noise-ring`](http://github.com/trezor/noise-rust)
/// for implementations based on rust-crypto and ring.
pub trait Backend {
    type Cipher: Cipher;
    type DH: DH;
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
            return Err(Error::InsufficientBuffer);
        }
        self.encrypt.encrypt_ad_in_place(&[], in_out, plaintext_len);
        Ok(())
    }

    pub fn decrypt(&mut self, in_out: &mut [u8]) -> Result<usize, Error> {
        if in_out.len() < TAG_LEN {
            return Err(Error::MalformedData);
        }
        self.decrypt
            .decrypt_ad_in_place(&[], in_out, in_out.len())
            .map_err(|()| Error::CryptoError)
    }

    pub fn handshake_hash(&self) -> &[u8; HANDSHAKE_HASH_LEN] {
        &self.handshake_hash
    }
}

impl<B: Backend> NoiseHandshake<Host, B> {
    pub fn start_pairing<'a>(
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
        let dest = dest.get_mut(..len).ok_or(Error::InsufficientBuffer)?;
        hss.write_message(payload, dest)?;
        let new = NoiseHandshake {
            hss,
            _phantom: PhantomData,
        };
        Ok((new, dest))
    }

    pub fn complete_pairing<'a>(
        &mut self,
        cred_store: &mut impl CredentialStore,
        buffer: &'a mut [u8],
        incoming_len: usize,
    ) -> Result<(NoiseCiphers<B>, &'a [u8]), Error> {
        if incoming_len != self.hss.get_next_message_overhead() {
            log::error!("Unexpected message length during handshake.");
            return Err(Error::MalformedData);
        }
        let incoming = buffer
            .get(..incoming_len)
            .ok_or(Error::InsufficientBuffer)?;
        self.hss.read_message(incoming, &mut [])?;

        // Look up static key based on remote keys, or generate a new one.
        let remote_static_key = self.hss.get_rs().ok_or(Error::CryptoError)?;
        let remote_ephemeral_key = self.hss.get_re().ok_or(Error::CryptoError)?;
        let (local_static, pairing_credential) =
            Self::credential_from_store(cred_store, &remote_ephemeral_key, &remote_static_key)?;
        self.hss.set_s(local_static);

        buffer.fill(0);
        let len = self.hss.get_next_message_overhead() + pairing_credential.len();
        let dest = buffer.get_mut(..len).ok_or(Error::InsufficientBuffer)?;
        self.hss
            .write_message(pairing_credential.as_slice(), dest)?;
        if !self.hss.completed() {
            log::error!("Handshake not completed.");
            return Err(Error::CryptoError);
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
        buf.resize(buf.capacity(), 0u8).unwrap();
        let result = cs.lookup(re.as_slice(), rs.as_slice(), buf.as_mut_slice());
        if let Some(found) = result {
            let found_key = <DHPrivKey<B> as U8Array>::from_slice(found.local_static_privkey);
            let found_credential = heapless::Vec::from_slice(found.auth_credential)
                .map_err(|_| Error::InsufficientBuffer)?;
            return Ok((found_key, found_credential));
        }
        buf.clear();
        let new_key = <B::DH as DH>::genkey();
        Ok((new_key, buf))
    }
}
