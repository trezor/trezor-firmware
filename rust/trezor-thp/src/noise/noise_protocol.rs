use noise_protocol::{CipherState, HandshakeState, patterns::noise_xx};

pub use noise_protocol::{Cipher, DH, Hash, U8Array};

use crate::{
    Error, channel::MAX_CREDENTIAL_LEN, credential::CredentialStore, util::prepare_zeroed,
};

use super::{Ciphers, HANDSHAKE_HASH_LEN, NoiseHandshake, PRIVKEY_LEN, PUBKEY_LEN, TAG_LEN};

/// Cryptography backend trait.
///
/// Please see [`noise-rust-crypto` and `noise-ring`](http://github.com/blckngm/noise-rust)
/// for implementations based on rust-crypto and ring.
pub trait NoiseProtocolBackend {
    /// Implementation of AES-256-GCM.
    type Cipher: Cipher;
    /// Implementation of X25519.
    type DH: DH;
    /// Implementation of SHA-256.
    type Hash: Hash;

    /// Fill entire destination with random bytes.
    fn random_bytes(dest: &mut [u8]);
}

type DHPrivKey<B> = <<B as NoiseProtocolBackend>::DH as DH>::Key;
type DHPubKey<B> = <<B as NoiseProtocolBackend>::DH as DH>::Pubkey;

pub struct NoiseProtocol<B: NoiseProtocolBackend> {
    hss: HandshakeState<B::DH, B::Cipher, B::Hash>,
}

pub struct NoiseCiphers<B: NoiseProtocolBackend> {
    encrypt: CipherState<B::Cipher>,
    decrypt: CipherState<B::Cipher>,
    handshake_hash: [u8; HANDSHAKE_HASH_LEN],
    remote_static_pubkey: [u8; PUBKEY_LEN],
}

impl<B: NoiseProtocolBackend> Ciphers for NoiseCiphers<B> {
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

impl<B: NoiseProtocolBackend> NoiseHandshake for NoiseProtocol<B> {
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
        let new = NoiseProtocol { hss };
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
}

impl<B: NoiseProtocolBackend> NoiseProtocol<B> {
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
